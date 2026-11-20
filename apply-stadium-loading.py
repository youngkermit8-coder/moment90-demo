from pathlib import Path
root = Path('public/studio')

def edit(file, groups):
    file = root / file
    content = file.read_text()
    for old, new in groups:
        assert content.count(old) == 1, (file, old)
        content = content.replace(old, new)
    file.write_text(content)

edit('extensions/collection.js', [
    ("async function load(){", """async function loadStadiumModel() {
 const status = $('load-text');
 async function download(url, loader) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('球场文件暂时不可用');
  const total = Number(response.headers.get('content-length'));
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0, previous = '';
  for (;;) {
   const {done, value} = await reader.read();
   if (done) break;
   chunks.push(value);
   size += value.byteLength;
   const progress = total ? Math.round(size / total * 100) + '%' : Math.floor(size / 1048576) + ' MB';
   if (progress !== previous) status.textContent = '正在加载三维球场 · ' + progress;
   previous = progress;
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
   bytes.set(chunk, offset);
   offset += chunk.byteLength;
  }
  status.textContent = '正在展开球场材质…';
  return loader.parseAsync(bytes.buffer, '');
 }
 try {
  const {MeshoptDecoder} = await import('../lib/meshopt_decoder.mjs');
  if (MeshoptDecoder.supported) {
   return await download('../models/stadium-web-v1.glb', new GLTFLoader().setMeshoptDecoder(MeshoptDecoder));
  }
 } catch (error) {
  console.warn('轻量球场暂时不可用，将载入原模型。', error);
 }
 return download('../models/stadium-v3.glb', new GLTFLoader());
}
async function load(){"""),
    ("},{rootMargin:'200px'});\nstadiumPreload", "},{rootMargin:'600px'});\nstadiumPreload")
])
f=root/'extensions/collection.js'
s=f.read_text()
a=s.index(" const response=await fetch('../models/stadium-v3.glb');")
b=s.index('\n model.traverse',a)
s=s[:a]+""" const gltf=await loadStadiumModel();
 model=gltf.scene;model.userData.roofRepair=repairRoofSurface(model);
 model.traverse(o=>{if(o.isMesh&&o.material?.name==='MI_st085_iron001_St.004')o.visible=false;});
 model.position.y-=20;size=new THREE.Vector3(340,85,340);"""+s[b:]
f.write_text(s)
edit('extensions/collection.html', [
    ('href="collection.css"', 'href="collection.css?v=stadium-web-1"'),
    ('src="collection.js"', 'src="collection.js?v=stadium-web-1"'),
])
edit('extensions/collection.css', [
    ('#stadium-loading{position:absolute;', '#stadium-loading{z-index:1;background:radial-gradient(ellipse,#0a10194d,#0a1019c4 76%),url(../assets/stadium.jpg) center/cover no-repeat;text-shadow:0 1px 8px #000;position:absolute;'),
])
edit('bayern/model-stadium-v2.js', [
    ("""  try {
    const gltf=await new GLTFLoader(manager).setDRACOLoader(draco).loadAsync(new URL('./assets/allianz-interactive/allianz.gltf',import.meta.url).href);""",
     """  try {
    const loader = new GLTFLoader(manager).setDRACOLoader(draco);
    draco.preload();
    const assets = new URL('./assets/allianz-interactive/', import.meta.url);
    let gltf;
    try {
      gltf = await loader.loadAsync(new URL('allianz-web-v1.gltf', assets).href);
    } catch (error) {
      console.warn('轻量球场暂时不可用，将载入原模型。', error);
      gltf = await loader.loadAsync(new URL('allianz.gltf', assets).href);
    }"""),
])
edit('bayern/journey-scene.js', [
    ("import('./model-stadium-v2.js')", "import('./model-stadium-v2.js?v=stadium-web-1')"),
])
edit('bayern/muller-journey.html', [
    ('moment-journey.js?v=21-match','moment-journey.js?v=stadium-web-1'),
])
edit('bayern/moment-journey.js', [
    ("const bayernEdition=document.body.dataset.edition==='muller';",
     """const bayernEdition=document.body.dataset.edition==='muller';
const initialView=search.get('view');
const openArenaOnLoad=bayernEdition&&initialView==='arena'&&search.get('tap')==='1';"""),
    ("import('./journey-scene.js?v=21-match')", "import('./journey-scene.js?v=stadium-web-1')"),
    ("""async function enterArena(){
  videoJourney?.leave();
  if(busy||unlocked<1)return;const token=++request,c=CARDS[selected];lastAction='arena';$('scene-error').hidden=true;
  sound.unlock();
  const wasPlaying=engine.getState().playing;engine.setPlaying(false);setBusy(true,'正在为你打开安联互动球场…');
  try{
    await engine.prepareArena();if(token!==request)return;
    unlocked=2;setBusy(false);updateStep('arena');engine.showArena(c);
    if(bayernEdition||c.club==='bayern')engine.showBayernCelebration();
    engine.setPlaying(wasPlaying);""",
     """async function enterArena({initial=false}={}){
  videoJourney?.leave();
  if(busy||(!initial&&unlocked<1))return;const token=++request,c=CARDS[selected];lastAction='arena';$('scene-error').hidden=true;
  sound.unlock();
  const wasPlaying=engine?.getState().playing??!reduced;engine?.setPlaying(false);
  setBusy(true,'正在为你打开安联互动球场…');
  try{
    const scene=await getEngine();
    await Promise.all([scene.prepareArena(),scene.prepareCard(c.club)]);
    if(token!==request)return;
    unlocked=2;setBusy(false);updateStep('arena');scene.showArena(c);
    if(bayernEdition||c.club==='bayern')scene.showBayernCelebration();
    scene.setPlaying(wasPlaying);"""),
    ("lastAction==='arena'?enterArena():awaken()", "lastAction==='arena'?enterArena({initial:openArenaOnLoad&&step==='scan'}):awaken()"),
    ("""warmSelectedCard();
// A tag/QR may eventually open a fixed card URL. This route resolves that binding;
// it does not claim to have performed a hardware NFC scan or an authenticity check.
const initialView=search.get('view');
if(bayernEdition&&initialView==='video')enterVideo();
else if(search.get('tap')==='1'){
  if(bayernEdition&&initialView==='arena')awaken().then(()=>{if(step==='card')enterArena();});
  else awaken();
}""",
     """// Direct arena and video routes prepare their own scenes in parallel.
if(openArenaOnLoad)enterArena({initial:true});
else if(bayernEdition&&initialView==='video')enterVideo();
else {
  warmSelectedCard();
  if(search.get('tap')==='1')awaken();
}"""),
])

f = root / 'extensions/collection.css'
s = f.read_text()
preview='z-index:1;background:radial-gradient(ellipse,#0a10194d,#0a1019c4 76%),url(../assets/stadium.jpg) center/cover no-repeat;text-shadow:0 1px 8px #000;'
f.write_text(s.replace('#stadium-loading{'+preview+'position:absolute;', '#stadium-loading{position:absolute;',1).rstrip()+'\n#stadium-loading{'+preview+'}\n')
