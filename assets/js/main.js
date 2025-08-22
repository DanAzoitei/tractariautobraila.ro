// Inject header & footer din fișiere separate + UX mică pentru meniu mobil, active nav, an curent
async function injectFragment(placeholderId, url){
  const host = document.querySelector(`#${placeholderId}`);
  if(!host) return;
  try{
    const res = await fetch(url, {cache:"reload"});
    const html = await res.text();
    host.outerHTML = html + `<div id="${placeholderId}"></div>`; // înlocuire curată
  }catch(e){ console.error("Nu pot încărca fragmentul:", url, e); }
}

function activateCurrentNav(){
  const active = document.querySelector('[data-active]')?.getAttribute('data-active');
  if(!active) return;
  const selector = `.main-nav a[data-nav="${active}"]`;
  const link = document.querySelector(selector);
  if(link) link.classList.add('active');
}

function wireMenuToggle(){
  const btn = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.main-nav');
  if(!btn || !nav) return;
  btn.addEventListener('click', () => {
    const open = nav.style.display === 'block';
    nav.style.display = open ? 'none' : 'block';
    btn.setAttribute('aria-expanded', String(!open));
  });
}

function setCopyYear(){
  const span = document.getElementById('y-copy');
  if(span) span.textContent = new Date().getFullYear();
}

(async function init(){
  await injectFragment('header-placeholder','/header.html');
  await injectFragment('footer-placeholder','/footer.html');
  // după injectare, leagă comportamente:
  activateCurrentNav();
  wireMenuToggle();
  setCopyYear();
})();
