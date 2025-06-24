const btn=document.getElementById('themeToggle');
if(btn){
  const cur=localStorage.getItem('theme')||'light';
  document.documentElement.setAttribute('data-bs-theme',cur);
  btn.innerText=cur==='light'?'Dark':'Light';
  btn.onclick=()=>{
    const now=document.documentElement.getAttribute('data-bs-theme');
    const next=now==='light'?'dark':'light';
    document.documentElement.setAttribute('data-bs-theme',next);
    localStorage.setItem('theme',next);
    btn.innerText=next==='light'?'Dark':'Light';
  };
}
