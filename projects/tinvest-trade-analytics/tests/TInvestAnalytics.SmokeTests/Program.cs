using System.Globalization;
using System.Net;
using System.Text;
using System.Text.Json;
using TInvestAnalytics;

var passed = 0;
void Check(string name, Action test)
{
    test();
    Console.WriteLine("PASS " + name);
    passed++;
}
void Equal<T>(T a, T b, string message)
{
    if (!EqualityComparer<T>.Default.Equals(a, b))
        throw new Exception(message + " expected=" + b + " actual=" + a);
}
DateTimeOffset day = DateTimeOffset.Parse("2026-11-10T12:00:00Z", CultureInfo.InvariantCulture);
DateTimeOffset from = day.AddDays(-2), to = day.AddDays(5);
string JsonOp(string id, string type, decimal price, decimal qty, decimal payment,
    string uid = "UID1", DateTimeOffset? date = null, string currency = "RUB")
{
    return JsonSerializer.Serialize(new
    {
        id, type, state = "OPERATION_STATE_EXECUTED", date = (date ?? day).ToString("O"),
        instrumentUid = uid, quantity = qty,
        price = new { units = price.ToString(CultureInfo.InvariantCulture), nano = 0 },
        payment = new { units = payment.ToString(CultureInfo.InvariantCulture), nano = 0,
            currency },
        trades = Array.Empty<object>()
    });
}
BrokerOperation Op(string id, string type, decimal price, decimal qty, decimal pay,
    string uid = "UID1", DateTimeOffset? dt = null)
{
    using var doc = JsonDocument.Parse(JsonOp(id, type, price, qty, pay, uid, dt));
    return OperationParser.Parse("TEST", doc.RootElement);
}
decimal Sum(PnlReport report, string name) =>
    report.Components.Where(x => x.Name == name).Sum(x => x.Amount);
var securities = new Dictionary<string, string> { ["UID1"] = "stock" };

Check("money nano precision and signed amounts", () =>
{
    using var doc = JsonDocument.Parse("""{"currency":"RUB","units":"-3","nano":-500000000}""");
    Equal(Money.FromJson(doc.RootElement).Amount, -3.5m, "negative money");
    Equal(new Money(3.000000001m, "RUB").Add(new Money(2m, "RUB")).Amount,
        5.000000001m, "decimal precision");
    bool fails = false;
    try { _ = new Money(1, "RUB").Add(new Money(1, "USD")); }
    catch (InvalidOperationException) { fails = true; }
    Equal(fails, true, "different currencies must fail");
});

Check("FIFO 100x100 + 100x110 -> sell 100x120 gives 2000", () =>
{
    var ops = new[] {
        Op("1","OPERATION_TYPE_BUY",100,100,-10000,dt:day.AddHours(-2)),
        Op("2","OPERATION_TYPE_BUY",110,100,-11000,dt:day.AddHours(-1)),
        Op("3","OPERATION_TYPE_SELL",120,100,12000)
    };
    var x = PnlCalculator.Calculate("TEST", ops, securities, from, to);
    Equal(Sum(x,"SECURITY_REALIZED_GROSS"),2000m,"FIFO gross");
    Equal(x.Status,"partial","not independently verified");
});

Check("short 10@120 then buy 15@100 gives 200 and new long", () =>
{
    var ops = new[] {
        Op("1","OPERATION_TYPE_SELL",120,10,1200,dt:day.AddHours(-2)),
        Op("2","OPERATION_TYPE_BUY",100,15,-1500,dt:day.AddHours(-1)),
        Op("3","OPERATION_TYPE_SELL",105,5,525)
    };
    var x=PnlCalculator.Calculate("TEST",ops,securities,from,to);
    Equal(Sum(x,"SECURITY_REALIZED_GROSS"),225m,"short profit 200 + long profit 25");
});

Check("partial fill operation: individual execution prices", () =>
{
    var obj = JsonSerializer.Serialize(new {
        id="C",type="OPERATION_TYPE_BUY",state="OPERATION_STATE_EXECUTED",
        date=day.ToString("O"), instrumentUid="UID1",quantity=3,
        payment=new {currency="RUB",units="-302",nano=0},
        trades=new object[]{
            new {tradeId="A",quantity=1,dateTime=day.AddMinutes(-1).ToString("O"),
                 price=new {units="100",nano=0}},
            new {tradeId="B",quantity=2,dateTime=day.ToString("O"),
                 price=new {units="101",nano=0}}
        }
    });
    using var doc=JsonDocument.Parse(obj);
    var trade=OperationParser.Parse("TEST",doc.RootElement);
    Equal(trade.Executions.Count,2,"two executions");
    Equal(trade.Executions.Sum(x=>x.Quantity*x.Price),302m,"notional sum");
});

Check("VM fees income vs tax/external deposits/funding", () =>
{
    var ops = new[] {
        Op("A","OPERATION_TYPE_ACCRUING_VARMARGIN",0,0,150,"FUT"),
        Op("B","OPERATION_TYPE_WRITING_OFF_VARMARGIN",0,0,-50,"FUT",day.AddMinutes(1)),
        Op("C","OPERATION_TYPE_BROKER_FEE",0,0,-4,"FUT",day.AddMinutes(2)),
        Op("D","OPERATION_TYPE_DIVIDEND",0,0,5,"DIV",day.AddMinutes(3)),
        Op("E","OPERATION_TYPE_INPUT",0,0,1000,"",day.AddMinutes(4)),
        Op("F","OPERATION_TYPE_TAX",0,0,-1,"",day.AddMinutes(5)),
        Op("G","OPERATION_TYPE_FUNDING",0,0,-3,"FUT",day.AddMinutes(6))
    };
    var report=PnlCalculator.Calculate("TEST",ops,null,from,to);
    Equal(Sum(report,"FUTURES_VM_SETTLED"),100m,"VM");
    Equal(Sum(report,"BROKER_FEES"),-4m,"fee");
    Equal(Sum(report,"FUNDING_UNVERIFIED_NOT_INCLUDED"),-3m,"funding separately");
    Equal(Sum(report,"EXTERNAL_FLOW_NOT_PNL"),1000m,"external cash separate");
    Equal(report.TotalsByCurrency["RUB"],101m,"no funding/tax/deposit in headline subtotal");
    Equal(report.Warnings.Any(x=>x.StartsWith("FUNDING_OVERLAP_UNVERIFIED")),true,
        "funding not double counted");
});


Check("FIFO carries prior inventory into a later reporting period", () =>
{
    var start = DateTimeOffset.Parse("2026-11-10T00:00:00Z", CultureInfo.InvariantCulture);
    var prior = Op("BUY-OLD","OPERATION_TYPE_BUY",100,4,-400,dt:start.AddDays(-1));
    var later = Op("SELL-TODAY","OPERATION_TYPE_SELL",125,4,500,dt:start.AddHours(12));
    var report = PnlCalculator.Calculate("TEST",new[]{prior,later},securities,start,start.AddDays(1));
    Equal(Sum(report,"SECURITY_REALIZED_GROSS"),100m,"prior purchase cost basis included");
    Equal(report.SourceOperationCount,1,"only current-period operation count");
});

Check("noncontiguous daily aggregation excludes selected date", () =>
{
    var start=DateTimeOffset.Parse("2026-11-10T00:00:00Z", CultureInfo.InvariantCulture);
    var ops=new[]{
        Op("B1","OPERATION_TYPE_BUY",100,4,-400,dt:start.AddDays(-1)),
        Op("S1","OPERATION_TYPE_SELL",125,4,500,dt:start.AddHours(12)),
        Op("B2","OPERATION_TYPE_BUY",100,3,-300,dt:start.AddDays(1).AddHours(9)),
        Op("S2","OPERATION_TYPE_SELL",110,3,330,dt:start.AddDays(1).AddHours(11))
    };
    var excluded=new HashSet<DateOnly>{new DateOnly(2026,11,11)};
    var report=DailyReporting.Calculate("TEST",ops,securities,start,start.AddDays(2),excluded);
    Equal(report.Days.Count,2,"two daily rows");
    Equal(report.Days[0].Included,true,"first day included");
    Equal(report.Days[1].Included,false,"second day excluded");
    Equal(report.SelectedSubtotalByCurrency["RUB"],100m,"only first-day profit");
    Equal(Sum(new PnlReport("TEST",start,start.AddDays(2),"partial",
        report.Days[1].Components,Array.Empty<string>(),0,0),"SECURITY_REALIZED_GROSS"),
        30m,"later day still independently computed");
});

Check("unknown instrument is not treated as an ordinary share", () =>
{
    var x=PnlCalculator.Calculate("TEST",new[]{
        Op("1","OPERATION_TYPE_BUY",100,1,-100),
        Op("2","OPERATION_TYPE_SELL",120,1,120)
    }, null, from, to);
    Equal(x.Components.Any(p=>p.Name=="SECURITY_REALIZED_GROSS"),false,"no guessed P&L");
    Equal(x.Warnings.Any(w=>w.StartsWith("UNCLASSIFIED_TRADE")),true,"flag quality");
});

Check("possible renamed IDs are flagged rather than silently combined", () =>
{
    var ops=new[]{
        Op("old","OPERATION_TYPE_BROKER_FEE",0,0,-1),
        Op("new","OPERATION_TYPE_BROKER_FEE",0,0,-1)
    };
    var p=PnlCalculator.Calculate("TEST",ops,null,from,to);
    Equal(p.Warnings.Any(x=>x.StartsWith("POSSIBLE_DUPLICATE")),true,"ambiguous duplicate");
});

Check("SQLite persistence, resume, idempotent import, revision", () =>
{
    var path=Path.Combine(Path.GetTempPath(),"tia_test_"+Guid.NewGuid().ToString("N")+".db");
    try
    {
        var store=new EvidenceStore(path);
        store.Initialize();
        string p1="{\"items\":["+JsonOp("a","OPERATION_TYPE_BROKER_FEE",0,0,-1)+
            "],\"hasNext\":false}";
        var k=store.GetCheckpoint("TEST",from,to);
        Equal(k.Complete,false,"new window incomplete");
        Equal(store.ImportPage("TEST",from,to,null,null,false,p1),1,"one");
        Equal(store.ImportPage("TEST",from,to,null,null,false,p1),1,"repeat page");
        var s=store.Stats();
        Equal(s.Pages,1L,"duplicate raw page not copied");
        Equal(s.Revisions,1L,"same op id and JSON no new revision");
        Equal(s.CurrentOperations,1L,"same id");
        Equal(store.GetCheckpoint("TEST",from,to).Complete,true,"window complete");
        store.RestartWindow("TEST",from,to);
        Equal(store.GetCheckpoint("TEST",from,to).Complete,false,"explicit refresh resets cursor but keeps raw evidence");
        Equal(store.LoadOperations("TEST",from,to).Count,1,"operation read");

        string p2="{\"items\":["+JsonOp("a","OPERATION_TYPE_BROKER_FEE",0,0,-2)+
            "],\"hasNext\":false}";
        store.ImportPage("TEST",from,to,null,null,false,p2);
        Equal(store.Stats().Revisions,2L,"changed source retained");
        Equal(store.LoadOperations("TEST",from,to)[0].Payment!.Value.Amount,-2m,"latest view updated");
        bool rejected=false;
        try { store.ImportPage("TEST",from,to,"c","c",true,p1); }
        catch (InvalidDataException) { rejected=true; }
        Equal(rejected,true,"cursor cycle rejected");

        var raw1000 = """{"totalAmountPortfolio":{"units":"1000","nano":0,"currency":"RUB"}}""";
        var raw1400 = """{"totalAmountPortfolio":{"units":"1400","nano":0,"currency":"RUB"}}""";
        var snap1=store.SavePortfolio("TEST",day.AddHours(-1),raw1000,"{}");
        var snap2=store.SavePortfolio("TEST",day.AddHours(1),raw1400,"{}");
        Equal(store.GetSnapshots("TEST").Count,2,"two snapshots persisted");
        Equal(store.HasCompleteOperationsWindow("TEST",snap1.ObservedAtUtc,snap2.ObservedAtUtc),
            true,"complete ingestion window covers snapshot range");
        var flow=Op("deposit","OPERATION_TYPE_INPUT",0,0,500,dt:day);
        var equity=PortfolioMath.Calculate(snap1,snap2,new[]{flow},true);
        Equal(equity.NetExternalFlows,500m,"deposit exclusion");
        Equal(equity.AbsoluteEquityPnl,-100m,"equity change minus deposit");
        Equal(equity.Quality,"provisional","not independently broker verified");
        var incomplete=PortfolioMath.Calculate(snap1,snap2,new[]{flow},false);
        Equal(incomplete.Quality,"partial","missing coverage reported");

    }
    finally
    {
        foreach(var suffix in new[]{"","-wal","-shm"})
        { try { File.Delete(path+suffix); } catch (IOException) { /* test temp cleanup best effort */ } }
    }
});

Check("read-only HTTP endpoint and schema contract", () =>
{
    using var handler=new FakeHandler();
    using var client=new TInvestClient("SYNTHETIC_TOKEN",handler:handler);
    var a=client.GetAccountsAsync().GetAwaiter().GetResult();
    Equal(TInvestClient.ParseAccounts(a).Count,1,"accounts response");
    Equal(handler.LastPath!.EndsWith("UsersService/GetAccounts",StringComparison.Ordinal),
        true,"read-only accounts route");
    var page=client.GetOperationsPageAsync("TEST",from,to,null).GetAwaiter().GetResult();
    Equal(TInvestClient.ParsePageCursor(page).HasNext,false,"parsed page");
    Equal(handler.LastPath!.EndsWith("OperationsService/GetOperationsByCursor",StringComparison.Ordinal),
        true,"read-only operations route");
    Equal(handler.AuthorizationScheme,"Bearer","authorization scheme");
});


Check("bot JSONL import, idempotency, collision guard and operational statistics", () =>
{
    var path=Path.Combine(Path.GetTempPath(),"tia_bot_"+Guid.NewGuid().ToString("N")+".db");
    try
    {
        string Row(string id,string kind,DateTimeOffset time)=>
            JsonSerializer.Serialize(new{
                schema="bot-event/v1",event_id=id,kind,observed_utc=time.ToString("O"),
                bot_id="BabidDemo",bot_version="sha:abcdef",run_id="RUN_1",
                account_ref="DEMO",instrument_uid="UID1",client_order_id="ORDER_"+id,
                side="BUY",qty_units="2",limit_price="100",fill_price="100"
            });
        var lines=string.Join("\n",new[]{
            Row("e1","order_submit",day),
            Row("e2","order_cancel_requested",day.AddSeconds(2)),
            Row("e3","order_submit",day.AddSeconds(3)),
            Row("e4","partial_fill",day.AddSeconds(4)),
            Row("e5","full_fill",day.AddSeconds(5)),
            Row("e6","error",day.AddSeconds(6))
        });
        var events=BotEventParser.ParseJsonLines(lines);
        Equal(events.Count,6,"six synthetic bot events");
        var store=new EvidenceStore(path);store.Initialize();
        Equal(store.ImportBotEvents(events),6,"first import");
        Equal(store.ImportBotEvents(events),0,"repeat import");
        bool collided=false;
        try { store.ImportBotEvents(new[]{BotEventParser.Parse(
            Row("e1","order_reject",day.AddSeconds(8)))}); }
        catch (InvalidDataException) { collided=true; }
        Equal(collided,true,"mutated event must not overwrite original");
        var loaded=store.LoadBotEvents("BabidDemo",from,to);
        Equal(loaded.Count,6,"original preserved");
        var summary=BotTelemetryAnalysis.Analyze("BabidDemo",loaded,from,to);
        Equal(summary.SubmittedOrders,2,"submit count");
        Equal(summary.CancelRequests,1,"cancel request");
        Equal(summary.PartialFillEvents,1,"partial fill event");
        Equal(summary.FullFillEvents,1,"full fill event");
        Equal(summary.RapidCancelRepostCandidates,1,"rapid repost");
        Equal(summary.ReportedRequestedUnits,4m,"requested volume");
        Equal(summary.ReportedFillDeltaUnits,4m,"reported incremental fills");
        Equal(summary.Quality,"unreconciled","no false P&L attribution");
    }
    finally
    {
        foreach(var suffix in new[]{"","-wal","-shm"})
        {try{File.Delete(path+suffix);}catch(IOException){}}
    }
});


Check("broker report async task and page evidence, commission summary", () =>
{
    string request = """{"generateBrokerReportResponse":{"taskId":"TASK_DEMO"}}""";
    Equal(BrokerReportParsing.ReadTaskId(request),"TASK_DEMO","generation response");
    string Row(string commission) => JsonSerializer.Serialize(new {
        orderId="ORDER",
        brokerCommission=new {currency="RUB",units=commission,nano=0},
        exchangeCommission=new {currency="RUB",units="1",nano=0},
        exchangeClearingCommission=new {currency="RUB",units="0",nano=0}
    });
    string Page(int index,string commission) =>
        "{\"getBrokerReportResponse\":{\"brokerReport\":["+Row(commission)+
        "],\"itemsCount\":2,\"pagesCount\":2,\"page\":"+index+"}}";
    var f=BrokerReportParsing.ReadPage(0,Page(0,"2"));
    Equal(f.ReturnedRows,1,"parsed one broker report row");
    var root=Path.Combine(Path.GetTempPath(),"tia_br_"+Guid.NewGuid().ToString("N")+".db");
    try
    {
        var store=new EvidenceStore(root);store.Initialize();
        store.SaveBrokerReportTask(new BrokerReportTask("TASK_DEMO","TEST",from,to,DateTimeOffset.UtcNow));
        store.SaveBrokerReportPage("TASK_DEMO",f);
        Equal(store.BrokerReportSummary("TASK_DEMO").Status,"partial","first page incomplete");
        var next=BrokerReportParsing.ReadPage(1,Page(1,"3"));
        store.SaveBrokerReportPage("TASK_DEMO",next);
        store.SaveBrokerReportPage("TASK_DEMO",next);
        var summary=store.BrokerReportSummary("TASK_DEMO");
        Equal(summary.PagesStored,2,"two unique pages");
        Equal(summary.ActualRows,2,"two raw report entries");
        Equal(summary.ExplicitCommissionsByCurrency["RUB"],7m,
              "2 + 3 broker and two exchange fees");
        Equal(summary.Status,"raw_complete_unreconciled","raw pages complete not cash reconciled");
    }
    finally
    {foreach(var suffix in new[]{"","-wal","-shm"}){try{File.Delete(root+suffix);}catch(IOException){}}}
});

Console.WriteLine($"All {passed} deterministic smoke tests passed.");

internal sealed class FakeHandler : HttpMessageHandler
{
    public string? LastPath {get;private set;}
    public string? AuthorizationScheme {get;private set;}
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        LastPath=request.RequestUri?.AbsolutePath;
        AuthorizationScheme=request.Headers.Authorization?.Scheme;
        string response=LastPath?.EndsWith("GetAccounts",StringComparison.Ordinal)==true
            ? """{"accounts":[{"id":"SYNTHETIC","name":"Sample","type":"ACCOUNT_TYPE_TINKOFF","status":"ACCOUNT_STATUS_OPEN"}]}"""
            : """{"items":[],"hasNext":false,"nextCursor":""}""";
        return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK){
            Content=new StringContent(response,Encoding.UTF8,"application/json")
        });
    }
}
