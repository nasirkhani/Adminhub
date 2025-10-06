(function (global) {
  'use strict';
  function div(a, b) { return ~~(a / b); }
  function g2d(gy, gm, gd) {
    var a = div(14 - gm, 12);
    var y = gy + 4800 - a;
    var m = gm + 12 * a - 3;
    var jdn = gd + div(153 * m + 2, 5) + 365 * y + div(y, 4) - div(y, 100) + div(y, 400) - 32045;
    return jdn;
  }
  function d2g(jdn) {
    var a = jdn + 32044;
    var b = div(4 * a + 3, 146097);
    var c = a - div(146097 * b, 4);
    var d = div(4 * c + 3, 1461);
    var e = c - div(1461 * d, 4);
    var m = div(5 * e + 2, 153);
    var day = e - div(153 * m + 2, 5) + 1;
    var month = m + 3 - 12 * div(m, 10);
    var year = 100 * b + d - 4800 + div(m, 10);
    return { gy: year, gm: month, gd: day };
  }
  function jalaliLeap(jy) {
    return (((jy - 474) % 2820 + 2820) % 2820 + 474 + 38) * 682 % 2816 < 682;
  }
  function j2d(jy, jm, jd) {
    jy = jy - (jy >= 0 ? 474 : 473);
    var epbase = jy % 2820;
    var epyear = epbase + 474;
    var mdays = (jm <= 7) ? ((jm - 1) * 31) : (6 * 31 + (jm - 7) * 30);
    return jd + mdays + div((epyear * 682 - 110) , 2816) + (epyear - 1) * 365 + div(epbase, 2820) * 1029983 + (1948320 - 1);
  }
  function d2j(jdn) {
    var depoch = jdn - j2d(475, 1, 1);
    var cycle = div(depoch, 1029983);
    var cyear = depoch % 1029983;
    var ycycle;
    if (cyear === 1029982) {
      ycycle = 2820;
    } else {
      var aux1 = div(cyear, 366);
      var aux2 = cyear % 366;
      ycycle = div((2134 * aux1 + 2816 * aux2 + 2815), 1028522) + aux1 + 1;
    }
    var jy = ycycle + 2820 * cycle + 474;
    if (jy <= 0) jy--;
    var yday = jdn - j2d(jy, 1, 1) + 1;
    var jm = (yday <= 186) ? Math.ceil(yday / 31) : Math.ceil((yday - 186) / 30) + 6;
    var jd = jdn - j2d(jy, jm, 1) + 1;
    return { jy: jy, jm: jm, jd: jd };
  }
  function toJalaali(gy, gm, gd) { var j = d2j(g2d(gy, gm, gd)); return { jy: j.jy, jm: j.jm, jd: j.jd }; }
  function toGregorian(jy, jm, jd) { var g = d2g(j2d(jy, jm, jd)); return { gy: g.gy, gm: g.gm, gd: g.gd }; }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function formatJ(jy, jm, jd, sep) { sep = sep || '/'; return jy + sep + pad(jm) + sep + pad(jd); }
  function formatG(gy, gm, gd, sep) { sep = sep || '-'; return gy + sep + pad(gm) + sep + pad(gd); }
  function parseJalali(str) {
    if (!str) return null;
    var s = str.trim().replace(/[.\-]/g, '/');
    var m = s.match(/^([0-9]{3,4})\/([0-9]{1,2})\/([0-9]{1,2})$/);
    if (!m) return null;
    var jy = parseInt(m[1], 10), jm = parseInt(m[2], 10), jd = parseInt(m[3], 10);
    if (jm < 1 || jm > 12) return null;
    var maxd = (jm <= 6) ? 31 : (jm <= 11 ? 30 : (jalaliLeap(jy) ? 30 : 29));
    if (jd < 1 || jd > maxd) return null;
    return { jy: jy, jm: jm, jd: jd };
  }
  function toPersianDigits(s) {
    var map = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'};
    return String(s).replace(/[0-9]/g, function(d){return map[d];});
  }
  global.JJ = { toJalaali: toJalaali, toGregorian: toGregorian, formatJ: formatJ, formatG: formatG, parseJalali: parseJalali, toPersianDigits: toPersianDigits };
})(this);
