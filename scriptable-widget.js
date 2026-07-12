// Dublin Bay Temp — iPhone home-screen widget for the Scriptable app.
// Install: get Scriptable (free, App Store) -> new script -> paste this ->
// add a Scriptable widget to your home screen -> choose this script.
// Data: Dublin Bay buoy via dublinbaybuoy.com; tides: Marine Institute.

const KEY = "sb_publishable_R5KkIpbiwNajUyx3I4aewQ_S4NI8hl3";
const COMPASS = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"];

function median(a){ const s=[...a].sort((x,y)=>x-y); return s[Math.floor(s.length/2)]; }
function fmtTime(d){
  return d.toLocaleTimeString("en-IE",{timeZone:"Europe/Dublin",hour:"2-digit",minute:"2-digit",hour12:false});
}

async function getReading(){
  const req = new Request("https://api.dublinbaybuoy.com/rest/v1/readings?select=timestamp,water_temp,wave_height,avg_wind,wind_dir&water_temp=not.is.null&order=timestamp.desc&limit=6");
  req.headers = {apikey: KEY};
  const rows = await req.loadJSON();
  for(const c of rows){
    const others = rows.filter(x=>x!==c).map(x=>x.water_temp);
    if(Math.abs(c.water_temp - median(others)) <= 1.5) return c;
  }
  return rows[0];
}

async function getNextTide(){
  const now = new Date(), to = new Date(+now + 30*36e5);
  const url = "https://erddap.marine.ie/erddap/tabledap/IMI_TidePrediction_HighLow.csv?time,tide_time_category&stationID=%22Dublin_Port%22"
    + "&time%3E=" + now.toISOString().slice(0,19) + "Z&time%3C" + to.toISOString().slice(0,19) + "Z";
  const txt = await new Request(url).loadString();
  const line = txt.trim().split("\n")[2];
  if(!line) return null;
  const c = line.split(",");
  return (c[1]==="HIGH"?"High ":"Low ") + fmtTime(new Date(c[0]));
}

const w = new ListWidget();
w.backgroundColor = new Color("#0B242C");
w.setPadding(14,16,12,16);
w.refreshAfterDate = new Date(Date.now() + 15*60*1000);
w.url = "https://dublinbaytemp.github.io/";

const ORANGE = new Color("#FF6B35"), FOAM = new Color("#EAF2F0"), MIST = new Color("#9FB8B9");

try{
  const r = await getReading();

  const head = w.addStack();
  head.centerAlignContent();
  const dot = head.addText("● ");
  dot.font = Font.boldSystemFont(9); dot.textColor = ORANGE;
  const title = head.addText("DUBLIN BAY");
  title.font = Font.semiboldSystemFont(11); title.textColor = MIST;
  head.addSpacer();
  const when = head.addText(fmtTime(new Date(r.timestamp)));
  when.font = Font.regularMonospacedSystemFont(10); when.textColor = MIST;

  w.addSpacer(6);
  const temp = w.addText(r.water_temp.toFixed(1) + "°C");
  temp.font = Font.mediumMonospacedSystemFont(34);
  temp.textColor = FOAM;
  temp.minimumScaleFactor = 0.6;

  const bits = [];
  if(r.avg_wind != null && r.wind_dir != null)
    bits.push(Math.round(r.avg_wind) + "kt " + COMPASS[Math.round(r.wind_dir/22.5)%16]);
  if(r.wave_height != null) bits.push(r.wave_height.toFixed(1) + "m");
  if(bits.length){
    w.addSpacer(3);
    const cond = w.addText(bits.join(" · "));
    cond.font = Font.regularMonospacedSystemFont(12);
    cond.textColor = MIST;
  }

  try{
    const tide = await getNextTide();
    if(tide){
      w.addSpacer(3);
      const t = w.addText("next tide " + tide);
      t.font = Font.regularSystemFont(12);
      t.textColor = MIST;
    }
  }catch(e){}
}catch(e){
  const err = w.addText("Buoy unreachable");
  err.font = Font.regularSystemFont(12);
  err.textColor = MIST;
}

if(config.runsInWidget) Script.setWidget(w);
else await w.presentSmall();
Script.complete();
