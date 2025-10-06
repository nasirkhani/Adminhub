(function () {
  'use strict';
  function qsAll(sel, root){ return Array.prototype.slice.call((root||document).querySelectorAll(sel)); }
  function findDateInputs() {
    var sels = [
      "input#duedate",
      "input.datepicker",
      "input.aui-date-picker",
      "input[data-aui-datepicker]",
      "input[id^='customfield_'][type='text']",
      "input[id^='customfield_'][type='date']"
    ];
    var inputs = [];
    sels.forEach(function(s){ inputs = inputs.concat(qsAll(s)); });
    var seen = new Set();
    return inputs.filter(function(inp){ if(seen.has(inp)) return false; seen.add(inp); return true; });
  }
  function formatGregorianForJira(g) { return JJ.formatG(g.gy, g.gm, g.gd, '-'); }
  function makeHint(el) { var hint = document.createElement('span'); hint.className = 'jalali-hint'; hint.textContent = ''; el.insertAdjacentElement('afterend', hint); return hint; }
  function updateHint(input, hint) {
    var val = input.value && input.value.trim();
    if (!val) { hint.textContent = ''; input.classList.remove('jalali-invalid'); return; }
    var gparts = val.match(/^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})$/);
    if (gparts) {
      var gy = parseInt(gparts[1],10), gm = parseInt(gparts[2],10), gd = parseInt(gparts[3],10);
      try {
        var j = JJ.toJalaali(gy, gm, gd);
        hint.innerHTML = 'شمسی: <span class="fa-num">' + JJ.toPersianDigits(JJ.formatJ(j.jy, j.jm, j.jd, '/')) + '</span>';
        input.classList.remove('jalali-invalid');
      } catch (e) { hint.textContent=''; }
      return;
    }
    var j = JJ.parseJalali(val);
    if (j) {
      hint.innerHTML = 'شمسی: <span class="fa-num">' + JJ.toPersianDigits(JJ.formatJ(j.jy, j.jm, j.jd, '/')) + '</span>';
      input.classList.remove('jalali-invalid');
    } else {
      hint.textContent = 'فرمت: 1404/07/14 (شمسی) یا 2025-10-06 (میلادی)';
      input.classList.add('jalali-invalid');
    }
  }
  function onBlurConvertIfJalali(e) {
    var input = e.target;
    var val = input.value && input.value.trim();
    if (!val) return;
    var j = JJ.parseJalali(val);
    if (j) {
      var g = JJ.toGregorian(j.jy, j.jm, j.jd);
      input.value = formatGregorianForJira(g);
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }
  function bindInput(input) {
    if (input._jalaliBound) return;
    input._jalaliBound = true;
    var hint = makeHint(input);
    updateHint(input, hint);
    input.addEventListener('input', function(){ updateHint(input, hint); });
    input.addEventListener('blur', onBlurConvertIfJalali);
  }
  function scan() { findDateInputs().forEach(bindInput); }
  function ready(fn) { if (document.readyState !== 'loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }
  ready(function(){
    scan();
    var obs = new MutationObserver(function(){ scan(); });
    obs.observe(document.body, { childList: true, subtree: true });
  });
})();
