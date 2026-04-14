// ═══════════════════════════════════════════════════════
//   EduPortal — admin.js
//   Admin panel JavaScript — cascade dropdowns via API
// ═══════════════════════════════════════════════════════

// ─────────────────────────────────────────────────────
//  CORE CASCADE FUNCTION
//  Usage:
//    cascadeLoad(
//      sourceId,       -- ID of the select that changed
//      targetId,       -- ID of the select to populate
//      urlPrefix,      -- API URL prefix, e.g. '/api/years?course_id='
//      labelPrefix,    -- Used in placeholder, e.g. 'Year'
//      valueField,     -- Field to display, e.g. 'year_number'
//      displayPrefix,  -- Text before value, e.g. 'Year' → "Year 1"
//      clearIds        -- Array of downstream select IDs to reset
//    )
// ─────────────────────────────────────────────────────
async function cascadeLoad(sourceId, targetId, urlPrefix, labelPrefix, valueField, displayPrefix, clearIds) {
  var sourceVal = document.getElementById(sourceId) ? document.getElementById(sourceId).value : '';
  var targetEl  = document.getElementById(targetId);
  if (!targetEl) return;

  // Reset downstream dropdowns first
  if (clearIds && clearIds.length) {
    clearIds.forEach(function(id) {
      var el = document.getElementById(id);
      if (el) el.innerHTML = '<option value="">— Select ' + id.replace(/[a-z]+([A-Z])/g, ' $1').trim() + ' —</option>';
    });
  }

  // Reset this target first
  targetEl.innerHTML = '<option value="">— Loading... —</option>';

  if (!sourceVal) {
    targetEl.innerHTML = '<option value="">— Select ' + labelPrefix + ' —</option>';
    return;
  }

  try {
    var res  = await fetch(urlPrefix + sourceVal);
    var data = await res.json();

    if (!data || data.length === 0) {
      targetEl.innerHTML = '<option value="">— No ' + labelPrefix + ' found —</option>';
      return;
    }

    targetEl.innerHTML = '<option value="">— Select ' + labelPrefix + ' —</option>';
    data.forEach(function(item) {
      var opt = document.createElement('option');
      opt.value = item.id;
      // Build label: "Year 1" or "Semester 2" or "Section A" or "Python (PY101)"
      if (valueField === 'name' && item.code) {
        opt.textContent = displayPrefix + ' ' + item[valueField] + ' (' + item.code + ')';
      } else if (displayPrefix) {
        opt.textContent = displayPrefix + ' ' + item[valueField];
      } else {
        opt.textContent = item[valueField];
      }
      targetEl.appendChild(opt);
    });
  } catch (e) {
    targetEl.innerHTML = '<option value="">— Error loading —</option>';
    console.error('cascadeLoad error:', e);
  }
}

// ─────────────────────────────────────────────────────
//  DOUBLE CASCADE (Semester → Section AND Subject together)
//  Used when one select should populate TWO targets
// ─────────────────────────────────────────────────────
async function cascadeLoadDouble(
  sourceId,
  targetId1, urlPrefix1, labelPrefix1, valueField1, displayPrefix1,
  targetId2, urlPrefix2, labelPrefix2, valueField2, displayPrefix2
) {
  var sourceVal = document.getElementById(sourceId) ? document.getElementById(sourceId).value : '';

  var target1 = document.getElementById(targetId1);
  var target2 = document.getElementById(targetId2);

  // Reset both
  if (target1) target1.innerHTML = '<option value="">— Loading... —</option>';
  if (target2) target2.innerHTML = '<option value="">— Loading... —</option>';

  if (!sourceVal) {
    if (target1) target1.innerHTML = '<option value="">— Select ' + labelPrefix1 + ' —</option>';
    if (target2) target2.innerHTML = '<option value="">— Select ' + labelPrefix2 + ' —</option>';
    return;
  }

  // Load both in parallel for speed
  try {
    var [res1, res2] = await Promise.all([
      fetch(urlPrefix1 + sourceVal),
      fetch(urlPrefix2 + sourceVal),
    ]);
    var [data1, data2] = await Promise.all([res1.json(), res2.json()]);

    // Populate target1 (Sections)
    if (target1) {
      target1.innerHTML = '<option value="">— Select ' + labelPrefix1 + ' —</option>';
      data1.forEach(function(item) {
        var opt = document.createElement('option');
        opt.value = item.id;
        opt.textContent = displayPrefix1 + ' ' + item[valueField1];
        target1.appendChild(opt);
      });
      if (data1.length === 0) target1.innerHTML = '<option value="">— No ' + labelPrefix1 + ' found —</option>';
    }

    // Populate target2 (Subjects)
    if (target2) {
      target2.innerHTML = '<option value="">— Select ' + labelPrefix2 + ' —</option>';
      data2.forEach(function(item) {
        var opt = document.createElement('option');
        opt.value = item.id;
        opt.textContent = item.code
          ? item[valueField2] + ' (' + item.code + ')'
          : item[valueField2];
        target2.appendChild(opt);
      });
      if (data2.length === 0) target2.innerHTML = '<option value="">— No ' + labelPrefix2 + ' found —</option>';
    }

  } catch (e) {
    if (target1) target1.innerHTML = '<option value="">— Error —</option>';
    if (target2) target2.innerHTML = '<option value="">— Error —</option>';
    console.error('cascadeLoadDouble error:', e);
  }
}

// ─────────────────────────────────────────────────────
//  TABLE FILTER for Subjects page (kept from old code)
// ─────────────────────────────────────────────────────
function adminFilterSubjects() {
  var courseId = document.getElementById('filterCourse') ? document.getElementById('filterCourse').value : '';
  var yearId   = document.getElementById('filterYear')   ? document.getElementById('filterYear').value   : '';
  var semId    = document.getElementById('filterSem')    ? document.getElementById('filterSem').value    : '';

  // Cascade year options (show/hide for subject filter — small set, ok to use old approach)
  var yearSel = document.getElementById('filterYear');
  if (yearSel) {
    yearSel.querySelectorAll('option').forEach(function(opt) {
      if (!opt.value) return;
      opt.style.display = (!courseId || opt.dataset.course === courseId) ? '' : 'none';
    });
    if (courseId && yearSel.options[yearSel.selectedIndex] &&
        yearSel.options[yearSel.selectedIndex].dataset.course !== courseId) {
      yearSel.value = ''; yearId = '';
    }
  }

  var semSel = document.getElementById('filterSem');
  if (semSel) {
    semSel.querySelectorAll('option').forEach(function(opt) {
      if (!opt.value) return;
      opt.style.display = (!yearId || opt.dataset.year === yearId) ? '' : 'none';
    });
    if (yearId && semSel.options[semSel.selectedIndex] &&
        semSel.options[semSel.selectedIndex].dataset.year !== yearId) {
      semSel.value = ''; semId = '';
    }
  }

  // Filter table rows
  var rows = document.querySelectorAll('#subjectsTable tbody tr');
  rows.forEach(function(row) {
    var matchCourse = !courseId || row.dataset.course === courseId;
    var matchYear   = !yearId   || row.dataset.year   === yearId;
    var matchSem    = !semId    || row.dataset.sem     === semId;
    row.style.display = (matchCourse && matchYear && matchSem) ? '' : 'none';
  });
}

// ─────────────────────────────────────────────────────
//  DOM READY
// ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {

  // Nav tab active state
  document.querySelectorAll('.nav-tab-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.nav-tab-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
    });
  });

  // Global table search (works on any page with id="tableSearch")
  var tableSearch = document.getElementById('tableSearch');
  if (tableSearch) {
    tableSearch.addEventListener('input', function() {
      var q = this.value.toLowerCase();
      // Find nearest table
      var table = document.querySelector('table tbody');
      if (table) {
        table.querySelectorAll('tr').forEach(function(row) {
          row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
        });
      }
    });
  }

  // Submissions tab search (teacher assignments page)
  var subSearch = document.getElementById('subSearch');
  if (subSearch) {
    subSearch.addEventListener('input', function() {
      var q = this.value.toLowerCase();
      document.querySelectorAll('#submissionsPane tbody tr').forEach(function(row) {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

});