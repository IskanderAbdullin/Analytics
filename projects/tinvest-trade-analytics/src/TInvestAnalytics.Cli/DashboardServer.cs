using System.Globalization;
using System.Net;
using System.Text;
using System.Text.Json;

namespace TInvestAnalytics;

/// <summary>
/// Loopback-only read-only dashboard. No remote CDN, broker requests, mutation API or
/// credential exposure. User starts it explicitly with the CLI serve command.
/// </summary>
public static class DashboardServer
{
    public static readonly string Html = """
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>TInvest Analytics — локальная аналитика</title>
<style>
:root{color-scheme:dark;font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif}
*{box-sizing:border-box}body{margin:0;background:#0c1221;color:#eef2fb;min-height:100vh}
header{padding:20px max(18px,calc((100vw - 1220px)/2));border-bottom:1px solid #27344d;display:flex;align-items:center;justify-content:space-between}
h1{margin:0;font-size:22px}h2{font-size:15px;margin:0 0 12px;color:#d7dff3}
small,.muted{color:#9eaccb;font-size:12px}
main{max-width:1220px;margin:auto;padding:24px 18px 64px}
.control{border:1px solid #27344d;border-radius:12px;padding:16px;display:flex;gap:12px;flex-wrap:wrap;align-items:end;background:#151d31}
label{display:flex;flex-direction:column;gap:6px;color:#aebbd8;font-size:12px}
input,select,button{font:inherit;border:1px solid #3a4a6b;color:#e8eeff;background:#0d1629;border-radius:8px;padding:9px 11px}
input[type=date]{min-width:145px}button{background:#3b63ed;border-color:#4774ff;cursor:pointer;font-weight:600}
button:disabled{opacity:.5;cursor:default}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:18px 0}
.kpi{background:#151d31;border:1px solid #27344d;border-radius:12px;padding:17px}
.kpi .label{color:#aebbd8;font-size:12px}
.kpi .value{font-size:23px;font-weight:700;margin-top:8px;overflow-wrap:anywhere}
.positive{color:#65d6a0}.negative{color:#fb8594}
.panel{background:#151d31;border:1px solid #27344d;border-radius:12px;padding:18px;margin:14px 0;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:11px 10px;border-bottom:1px solid #27344d;text-align:left}
th{color:#acbbd9;font-weight:500}td.num{text-align:right;font-variant-numeric:tabular-nums}
#chart{width:100%;height:240px;display:block}
.warning{border-left:3px solid #e3b667;background:#28251f;padding:12px 15px;border-radius:6px;color:#f4deb1;font-size:13px;margin:10px 0}
.status{margin-left:auto;color:#acbbd9;font-size:12px}
footer{color:#8c99b7;font-size:12px;margin-top:22px}
</style>
</head>
<body>
<header><h1>TInvest Analytics <small>локальная версия 0.6</small></h1><small>только чтение · 127.0.0.1</small></header>
<main>
<div class="control">
<label>Счёт<select id="account"></select></label>
<label>С даты (UTC)<input type="date" id="from"></label>
<label>По дату (UTC)<input type="date" id="to"></label>
<label>Исключить дни (через запятую)<input id="exclude" placeholder="2026-11-14"></label>
<button id="refresh">Рассчитать</button>
<span class="status" id="status">История локальная, без связи с брокером</span>
</div>
<div class="warning">Предварительные суммы: реализованный FIFO по классифицированным бумагам + денежная вариационная маржа + комиссии и инвестиционные поступления. Это <b>не полный P&amp;L портфеля</b>, пока не проведены оценка открытых позиций и сверка брокерских документов. Фандинг не добавляется без проверки двойного учёта.</div>
<section class="kpis">
<div class="kpi"><div class="label">Расчётный промежуточный результат (RUB)</div><div class="value" id="total">—</div></div>
<div class="kpi"><div class="label">Количество операций в периоде</div><div class="value" id="count">—</div></div>
<div class="kpi"><div class="label">Дней в выборке</div><div class="value" id="days">—</div></div>
<div class="kpi"><div class="label">Качество данных</div><div class="value" id="quality">—</div></div>
</section>
<div class="panel"><h2>Динамика дневного результата (RUB)</h2><canvas id="chart" width="1100" height="240"></canvas><small>Нет доходности открытых позиций без актуальной рыночной переоценки. Исключённые дни отображаются серыми.</small></div>
<div class="panel"><h2>Инструменты и источники результата</h2><table><thead><tr><th>Инструмент / раздел</th><th>Компонент</th><th>Валюта</th><th style="text-align:right">Сумма</th></tr></thead><tbody id="instrument-table"></tbody></table></div>
<div class="panel"><h2>Дни и операции</h2><table><thead><tr><th>Дата UTC</th><th>В выборке</th><th style="text-align:right">Результат RUB</th><th style="text-align:right">Операций</th></tr></thead><tbody id="daily-table"></tbody></table></div>
<div class="panel"><h2>Сохранённые оценки портфеля</h2><table><thead><tr><th>Снимок</th><th>Дата наблюдения</th><th style="text-align:right">Стоимость</th></tr></thead><tbody id="snapshots-table"></tbody></table></div>
<div class="panel"><h2>Ограничения и предупреждения</h2><div id="warnings" class="muted">Выберите счёт и период</div></div>
<footer>Локальное приложение. В репозитории — код и синтетические тесты; реальные операции и токены остаются на компьютере пользователя. Все даты на этом экране UTC.</footer>
</main>
<script>
"use strict";
const $=id=>document.getElementById(id);
const money=n=>Number(n).toLocaleString("ru-RU",{minimumFractionDigits:2,maximumFractionDigits:2})+" ₽";
const daySum=(d)=>d.components.filter(x=>["SECURITY_REALIZED_GROSS","FUTURES_VM_SETTLED","BROKER_FEES","MARGIN_FINANCING","INVESTMENT_INCOME"].includes(x.name)&&x.currency==="RUB").reduce((s,x)=>s+Number(x.amount),0);
function td(row,value,cls){const n=document.createElement("td");n.textContent=String(value);if(cls)n.className=cls;row.append(n)}
function line(tbody,values,cls){const row=document.createElement("tr");values.forEach((v,i)=>td(row,v,i===values.length-1?"num":""));if(cls)row.className=cls;tbody.append(row)}
async function get(path){const r=await fetch(path,{cache:"no-store",credentials:"omit"});if(!r.ok)throw new Error("HTTP "+r.status);return await r.json()}
function draw(rows){
 const c=$("chart"),ctx=c.getContext("2d");
 ctx.clearRect(0,0,c.width,c.height);
 const n=rows.length;if(!n){ctx.fillStyle="#adbad6";ctx.fillText("Нет данных",20,30);return}
 const vals=rows.map(x=>daySum(x));const max=Math.max(1,...vals.map(Math.abs));const zero=120;
 ctx.strokeStyle="#546581";ctx.beginPath();ctx.moveTo(26,zero);ctx.lineTo(c.width-10,zero);ctx.stroke();
 const w=(c.width-40)/n;
 rows.forEach((d,i)=>{
  const v=vals[i],h=Math.abs(v)/max*100,x=26+i*w+1;
  ctx.fillStyle=d.included?(v>=0?"#44d09b":"#ee7081"):"#59647b";
  ctx.fillRect(x,v>=0?zero-h:zero,Math.max(2,w-3),Math.max(1,h));
  if(n<=18){ctx.fillStyle="#abb8d2";ctx.font="10px system-ui";ctx.fillText(d.utc_day.slice(5),x,c.height-12)}
 });
 ctx.fillStyle="#a6b3d1";ctx.font="11px system-ui";ctx.fillText("+ "+money(max),4,14);ctx.fillText("− "+money(max),4,232);
}
async function loadAccounts(){
 const options=await get("/api/accounts");$("account").replaceChildren();
 for(const a of options){const o=document.createElement("option");o.value=a.key;o.textContent=a.label;$("account").append(o)}
 if(!options.length){$("status").textContent="База пуста: выполните импорт через CLI";$("refresh").disabled=true;return}
 await refresh();
}
async function refresh(){
 try{
  $("status").textContent="Расчёт из локальной SQLite...";
  const a=encodeURIComponent($("account").value),f=$("from").value,t=$("to").value,ex=encodeURIComponent($("exclude").value);
  const report=await get("/api/daily?account="+a+"&from="+f+"&to="+t+"&exclude="+ex);
  const snapshots=await get("/api/snapshots?account="+a);
  const subtotal=report.selected_subtotal_by_currency.RUB;
  $("total").textContent=subtotal===undefined?"Нет RUB":money(subtotal);
  $("total").className="value "+(Number(subtotal)>=0?"positive":"negative");
  $("count").textContent=report.days.reduce((s,x)=>s+(x.included?x.operation_count:0),0);
  $("days").textContent=report.days.filter(x=>x.included).length+" / "+report.days.length;
  $("quality").textContent=report.quality;
  draw(report.days);
  const dt=$("daily-table");dt.replaceChildren();
  const it=$("instrument-table");it.replaceChildren();
  const grouped=new Map();const warns=new Set();
  for(const d of report.days){
   line(dt,[d.utc_day,d.included?"Да":"Нет",money(daySum(d)),d.operation_count]);
   if(d.included)for(const x of d.components){const key=x.scope+"|"+x.name+"|"+x.currency;grouped.set(key,(grouped.get(key)||0)+Number(x.amount))}
   for(const w of d.warnings)if(!w.startsWith("UNCLASSIFIED_TRADE"))warns.add(w);
  }
  [...grouped.entries()].sort((a,b)=>Math.abs(b[1])-Math.abs(a[1])).forEach(([key,sum])=>{
   const [scope,name,ccy]=key.split("|");line(it,[scope,name,ccy,sum.toFixed(2)]);
  });
  const st=$("snapshots-table");st.replaceChildren();
  for(const x of snapshots)line(st,["#"+x.id,x.observed_at_utc,money(x.equity.amount)+" "+x.equity.currency]);
  $("warnings").replaceChildren();
  if(warns.size===0){$("warnings").textContent="Дополнительных предупреждений не обнаружено";}else{
    for(const w of [...warns].slice(0,30)){const p=document.createElement("p");p.textContent=w;$("warnings").append(p)}
  }
  $("status").textContent="Данные локальные, без онлайн-обновления";
 }catch(e){$("status").textContent="Ошибка: "+e.message}
}
$("refresh").addEventListener("click",refresh);
const today=new Date().toISOString().slice(0,10);
$("to").value=today;
const start=new Date(Date.now()-7*86400000);$("from").value=start.toISOString().slice(0,10);
loadAccounts().catch(e=>$("status").textContent="Ошибка загрузки: "+e.message);
</script>
</body></html>
""";

    private static JsonSerializerOptions JsonOptions() => new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    public static async Task RunAsync(EvidenceStore store, string? assetMapFile, int port)
    {
        if (port < 1024 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port));
        IReadOnlyDictionary<string, string> types = new Dictionary<string, string>();
        if (assetMapFile is not null)
            types = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(assetMapFile)) ??
                new Dictionary<string, string>();
        using var listener = new HttpListener();
        listener.Prefixes.Add($"http://127.0.0.1:{port}/");
        listener.Start();
        using var cts = new CancellationTokenSource();
        ConsoleCancelEventHandler handler = (_, a) => { a.Cancel = true; cts.Cancel(); listener.Stop(); };
        Console.CancelKeyPress += handler;
        Console.WriteLine($"Local read-only dashboard: http://127.0.0.1:{port}/ (Ctrl+C to stop)");
        try
        {
            while (!cts.IsCancellationRequested)
            {
                HttpListenerContext context;
                try { context = await listener.GetContextAsync().ConfigureAwait(false); }
                catch (HttpListenerException) when (cts.IsCancellationRequested) { break; }
                await Respond(context, store, types).ConfigureAwait(false);
            }
        }
        finally { Console.CancelKeyPress -= handler; }
    }

    private static async Task Respond(HttpListenerContext context, EvidenceStore store,
        IReadOnlyDictionary<string, string> assetTypes)
    {
        var res = context.Response;
        res.Headers["Cache-Control"] = "no-store, max-age=0";
        res.Headers["X-Content-Type-Options"] = "nosniff";
        res.Headers["Referrer-Policy"] = "no-referrer";
        res.Headers["X-Frame-Options"] = "DENY";
        res.Headers["Content-Security-Policy"] =
            "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; " +
            "connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'";
        try
        {
            if (context.Request.HttpMethod != "GET")
            {
                await Send(res,405,"text/plain","Only GET is supported.");
                return;
            }
            string path = context.Request.Url?.AbsolutePath ?? "/";
            if (path == "/")
            {
                await Send(res,200,"text/html; charset=utf-8",Html);
                return;
            }
            var query = context.Request.QueryString;
            var accounts = store.LocalAccounts();
            var byKey = accounts.ToDictionary(id => OperationParser.Hash(id)[..16], id => id);
            if (path == "/api/accounts")
            {
                await SendJson(res,accounts.Select(x => new {
                    key = OperationParser.Hash(x)[..16],label=PnlCalculator.Mask(x)
                }).ToList());
                return;
            }
            string key = query["account"] ?? "";
            if (!byKey.TryGetValue(key, out string? account))
            {
                await Send(res,400,"text/plain","Unknown local account.");
                return;
            }
            if (path == "/api/snapshots")
            {
                await SendJson(res,store.GetSnapshots(account).Select(x=>new {
                    id=x.Id,observed_at_utc=x.ObservedAtUtc,equity=x.Equity
                }).ToArray());
                return;
            }
            if (path == "/api/daily")
            {
                string? f=query["from"], t=query["to"];
                if (!DateOnly.TryParseExact(f,"yyyy-MM-dd",CultureInfo.InvariantCulture,
                    DateTimeStyles.None,out var first) ||
                    !DateOnly.TryParseExact(t,"yyyy-MM-dd",CultureInfo.InvariantCulture,
                    DateTimeStyles.None,out var last) || last<first)
                    throw new ArgumentException("Use valid from/to dates in YYYY-MM-DD format.");
                var begin = new DateTimeOffset(first.ToDateTime(TimeOnly.MinValue),TimeSpan.Zero);
                var end = new DateTimeOffset(last.ToDateTime(TimeOnly.MinValue),TimeSpan.Zero).AddDays(1);
                var excluded=new HashSet<DateOnly>();
                foreach(var day in (query["exclude"] ?? "").Split(',',
                    StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries))
                    excluded.Add(DateOnly.ParseExact(day,"yyyy-MM-dd",CultureInfo.InvariantCulture));
                var ops=store.LoadOperations(account,DateTimeOffset.MinValue,end);
                var daily=DailyReporting.Calculate(account,ops,assetTypes,begin,end,excluded);
                await SendJson(res,daily);
                return;
            }
            await Send(res,404,"text/plain","Not found");
        }
        catch (Exception e) when (e is ArgumentException or FormatException or InvalidOperationException)
        {
            await Send(res,400,"text/plain","Invalid request. Check date and account settings.");
        }
        catch (Exception)
        {
            await Send(res,500,"text/plain","Internal query error. Check local CLI diagnostics.");
        }
    }

    private static Task SendJson(HttpListenerResponse res, object value) =>
        Send(res,200,"application/json; charset=utf-8",JsonSerializer.Serialize(value,JsonOptions()));

    private static async Task Send(HttpListenerResponse response, int status,
        string contentType, string content)
    {
        response.StatusCode=status;
        response.ContentType=contentType;
        byte[] body=Encoding.UTF8.GetBytes(content);
        response.ContentLength64=body.Length;
        try { await response.OutputStream.WriteAsync(body).ConfigureAwait(false); }
        finally { response.Close(); }
    }
}

public sealed partial class EvidenceStore
{
    public IReadOnlyList<string> LocalAccounts()
    {
        using var c = Open();
        using var q = Command(c,null, """
            SELECT DISTINCT account_id FROM (
                SELECT account_id FROM sync_windows
                UNION ALL SELECT account_id FROM current_operations
                UNION ALL SELECT account_id FROM portfolio_observations
                UNION ALL SELECT account_id FROM broker_report_tasks
            ) ORDER BY account_id
            """);
        using var reader = q.ExecuteReader();
        var ids=new List<string>();
        while(reader.Read())ids.Add(reader.GetString(0));
        return ids;
    }
}
