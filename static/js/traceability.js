document.addEventListener("DOMContentLoaded",()=>{
 const total=document.querySelector('[name="items-TOTAL_FORMS"]');
 document.querySelector('[data-add-item]')?.addEventListener('click',()=>{
  const n=Number(total.value); if(n>=100)return;
  const html=document.querySelector('[data-empty-item]').innerHTML.replaceAll('__prefix__',String(n));
  document.querySelector('[data-items]').insertAdjacentHTML('beforeend',html);total.value=n+1;
 });
 document.querySelectorAll('form').forEach(form=>form.addEventListener('submit',()=>{
  form.setAttribute('aria-busy','true');
 }));
});
