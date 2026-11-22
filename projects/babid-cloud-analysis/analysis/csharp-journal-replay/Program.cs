using Babid01;

internal static class Program
{
    private static readonly DateTime T0 = new(2026, 1, 1, 10, 0, 0, DateTimeKind.Utc);
    private static int _checks;

    private static void Require(bool value, string description)
    {
        _checks++;
        if (!value) throw new InvalidOperationException("Journal source test failed: " + description);
    }

    private static (Journal Journal, Position Position, Order Order) CanceledOpening()
    {
        var journal = new Journal(null);
        Position position = journal.NewPosition(Side.Sell);
        Order order = journal.NewOrder(position, closing: false, side: Side.Sell,
            kind: OrderKind.Limit, price: 99m, volume: 40, now: T0);
        order.State = OrderState.Cancel;
        order.UpdatedUtc = T0;
        return (journal, position, order);
    }

    private static void TestPruneGrace()
    {
        var (journal, position, order) = CanceledOpening();
        journal.Prune(T0.AddMilliseconds(4999), TimeSpan.FromSeconds(5));
        Require(position.OpenOrders.Contains(order), "cancel must survive grace");
        journal.Prune(T0.AddSeconds(5), TimeSpan.FromSeconds(5));
        Require(!position.OpenOrders.Contains(order), "cancel zero order detached after grace");
        Require(journal.Positions.Count == 0, "zero empty position removed");
    }

    private static void TestArchiveRetainsRequestLookupAndLateFill()
    {
        var (journal, position, order) = CanceledOpening();
        int archiveCallbacks = 0;
        journal.Prune(T0.AddSeconds(6), TimeSpan.FromSeconds(5),
            _ => archiveCallbacks++);
        Require(archiveCallbacks == 1, "one archive callback for zero opening order");
        Require(!position.OpenOrders.Contains(order), "order removed from position");
        Require(journal.TryGet(order.RequestId, out Order? found) &&
            ReferenceEquals(found, order), "request id still maps to detached order");
        order.Fills.Add(new Fill {
            TradeId = "fictional-execution", Lots = 2, Price = 99m, TimeUtc = T0,
        });
        Require(order.Filled == 2, "late trade updated detached order object");
        Require(journal.NetLots == 0, "detached fill does not alter journal net lots");
        journal.Restore(order);
        Require(position.OpenOrders.Contains(order), "explicit restore reattaches");
        Require(journal.NetLots == -2, "explicit restore reinstates signed lots");
    }

    private static void TestSilentPrecreditBlocksPruneWithoutDoubleCount()
    {
        var (journal, position, order) = CanceledOpening();
        order.FilledByState = 2;
        Require(!order.FillsSynchronized, "state lots without trade not synchronized");
        journal.Prune(T0.AddSeconds(45), TimeSpan.FromSeconds(5));
        Require(position.OpenOrders.Contains(order), "state-precredited order not pruned");
        Require(journal.NetLots == -2, "broker-state lots already counted in journal");
        order.Fills.Add(new Fill { TradeId = "fictional-second", Lots = 2,
            Price = 99m, TimeUtc = T0 });
        Require(order.FillsSynchronized, "late real trade synchronizes the order");
        Require(journal.NetLots == -2, "late trade cannot double-count journal lots");
    }

    private static void TestUnresolvedFlagsBlockPrune()
    {
        foreach (Action<OrderTracking> setFlag in new Action<OrderTracking>[] {
            x => x.NeedsCheck = true,
            x => x.ResyncNeeded = true,
            x => x.QueryInFlight = true,
        })
        {
            var (journal, position, order) = CanceledOpening();
            setFlag(order.Track);
            journal.Prune(T0.AddSeconds(20), TimeSpan.FromSeconds(5));
            Require(position.OpenOrders.Contains(order), "unresolved flag blocks prune");
        }
    }

    private static void TestAlreadyTradedOrderNotPruned()
    {
        var (journal, position, order) = CanceledOpening();
        order.Fills.Add(new Fill { TradeId = "fictional-third", Lots = 2,
            Price = 99m, TimeUtc = T0 });
        journal.Prune(T0.AddSeconds(20), TimeSpan.FromSeconds(5));
        Require(position.OpenOrders.Contains(order), "nonzero filled order cannot be pruned");
    }

    public static int Main()
    {
        TestPruneGrace();
        TestArchiveRetainsRequestLookupAndLateFill();
        TestSilentPrecreditBlocksPruneWithoutDoubleCount();
        TestUnresolvedFlagsBlockPrune();
        TestAlreadyTradedOrderNotPruned();
        Console.WriteLine($"PASS: {_checks} assertions against pinned, actual Journal.cs and Domain.cs source.");
        Console.WriteLine("CONSTRAINT: Does not execute Engine.Orders, broker API, or real incident data.");
        return 0;
    }
}
