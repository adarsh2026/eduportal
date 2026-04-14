// ═══════════════════════════════════════════════════════
//   EduPortal — app.js  (complete)
// ═══════════════════════════════════════════════════════

/* ── Utilities ──────────────────────────────────────── */
const WEEKDAYS   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const MONTHS     = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const MONS_SHORT = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function todayISO() { return new Date().toISOString().split('T')[0]; }
function isoDate(d) { return d.toISOString().split('T')[0]; }
function fmtDate(iso) {
  const d = new Date(iso + 'T00:00:00');
  return d.getDate() + ' ' + MONS_SHORT[d.getMonth()] + ' ' + d.getFullYear();
}
function fmtRangeLabel(from, to) {
  const f = fmtDate(isoDate(from));
  const t = fmtDate(isoDate(to));
  return f === t ? f : f + ' – ' + t;
}

/* ── Note Download ──────────────────────────────────── */
function downloadNote(title, content) {
  const blob = new Blob([content], { type:'text/plain' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = title.replace(/\s+/g,'_') + '.txt';
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(a.href);
}

/* ── Delete Confirm ─────────────────────────────────── */
function confirmDelete(name) { return confirm('Delete "' + name + '"?'); }

// ═══════════════════════════════════════════════════════
//   TEACHER CALENDAR  (teacher_attendence.html)
// ═══════════════════════════════════════════════════════

let calYear      = new Date().getFullYear();
let calMonth     = new Date().getMonth();
let selectedDate = null;

function buildCalStrip() {
  const strip = document.getElementById('calStrip');
  const label = document.getElementById('monthLabel');
  if (!strip) return;

  label.textContent = MONTHS[calMonth] + ' ' + calYear;
  strip.innerHTML   = '';
  const today       = todayISO();
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();

  for (let d = 1; d <= daysInMonth; d++) {
    const mm  = String(calMonth + 1).padStart(2,'0');
    const dd  = String(d).padStart(2,'0');
    const iso = `${calYear}-${mm}-${dd}`;
    const dow = new Date(calYear, calMonth, d).getDay();
    const hasData  = (typeof DATES_WITH_DATA !== 'undefined') && DATES_WITH_DATA.has(iso);
    const isActive = iso === selectedDate;
    const isToday  = iso === today;

    const el = document.createElement('div');
    el.className    = 'cal-day' + (isActive ? ' active' : '') + (hasData ? ' has-data' : '');
    el.dataset.date = iso;
    el.innerHTML = `
      <span class="cal-weekday">${WEEKDAYS[dow]}</span>
      <span class="cal-num">${d}</span>
      <span class="cal-month-tag" ${isToday ? 'style="color:var(--accent);font-weight:700;"' : ''}>
        ${isToday ? 'Today' : MONTHS[calMonth].slice(0,3)}
      </span>`;
    el.addEventListener('click', function() {
      selectedDate = iso;
      buildCalStrip();
      renderRecordsPanel();
      scrollCalTo(iso);
    });
    strip.appendChild(el);
  }
  setTimeout(() => scrollCalTo(selectedDate || today), 60);
}

function scrollCalTo(iso) {
  const strip = document.getElementById('calStrip');
  if (!strip || !iso) return;
  const el = strip.querySelector(`[data-date="${iso}"]`);
  if (el) el.scrollIntoView({ behavior:'smooth', inline:'center', block:'nearest' });
}

function changeMonth(delta) {
  calMonth += delta;
  if (calMonth > 11) { calMonth = 0;  calYear++; }
  if (calMonth <  0) { calMonth = 11; calYear--; }
  selectedDate = null;
  buildCalStrip();
  const rp = document.getElementById('recordsPanel');
  if (rp) rp.innerHTML = '<div class="empty-state"><i class="bi bi-calendar2-week"></i><p>Select Date</p></div>';
  const sl = document.getElementById('selectedDateLabel');
  if (sl) sl.textContent = '';
}

function slideStrip(n) {
  const s = document.getElementById('calStrip');
  if (s) s.scrollBy({ left: n * 72, behavior:'smooth' });
}

/* ── Teacher Records Panel ─────────────────────────── */
function renderRecordsPanel() {
  const panel = document.getElementById('recordsPanel');
  if (!panel || !selectedDate) return;

  const courseFilterEl = document.getElementById('recordCourseFilter');
  const courseFilter   = courseFilterEl ? (parseInt(courseFilterEl.value) || null) : null;

  const d   = new Date(selectedDate + 'T00:00:00');
  const lbl = document.getElementById('selectedDateLabel');
  if (lbl) lbl.textContent = WEEKDAYS[d.getDay()] + ', ' + d.getDate() + ' ' + MONTHS[d.getMonth()] + ' ' + d.getFullYear();

  if (typeof ALL_RECORDS === 'undefined') return;

  let dayRecords = ALL_RECORDS.filter(r => r.date === selectedDate);
  if (courseFilter) dayRecords = dayRecords.filter(r => r.course_id === courseFilter);

  if (dayRecords.length === 0) {
    panel.innerHTML = '<div class="empty-state"><i class="bi bi-calendar-x"></i><p>No Record for this Date </p></div>';
    return;
  }

  let html = '<div class="att-records-list">';
  dayRecords.forEach(r => {
    const name       = (typeof STUDENT_MAP !== 'undefined') ? (STUDENT_MAP[r.student_id] || 'Student #'+r.student_id) : 'Student #'+r.student_id;
    const courseName = (typeof COURSE_MAP  !== 'undefined') ? (COURSE_MAP[r.course_id]   || 'Course #'+r.course_id)   : 'Course #'+r.course_id;
    const badge      = r.status === 'present'
      ? '<span class="badge-present"> Present</span>'
      : '<span class="badge-absent">Absent</span>';
    html += `
      <div class="att-record-card">
        <div class="att-record-avatar">${name[0].toUpperCase()}</div>
        <div style="flex:1;">
          <div class="att-record-name">${name}</div>
          <div class="att-record-sub">ID #${r.student_id} &nbsp;<span class="badge-course">${courseName}</span></div>
        </div>
        <div>${badge}</div>
      </div>`;
  });
  html += '</div>';
  panel.innerHTML = html;
}

// ═══════════════════════════════════════════════════════
//   MARK ATTENDANCE FORM  (teacher_attendence.html)
// ═══════════════════════════════════════════════════════

function loadMarkStudents() {
  const courseId = document.getElementById('markCourseSelect').value;
  const dateVal  = document.getElementById('markDateInput').value;
  const errorDiv = document.getElementById('markError');
  errorDiv.style.display = 'none';

  if (!courseId) { errorDiv.textContent = '⚠️ Select Course'; errorDiv.style.display = 'block'; return; }
  if (!dateVal)  { errorDiv.textContent = '⚠️ Select Date';         errorDiv.style.display = 'block'; return; }

  document.getElementById('markFormCourseId').value = courseId;
  document.getElementById('markFormDate').value     = dateVal;

  const sel        = document.getElementById('markCourseSelect');
  const courseName = sel.options[sel.selectedIndex].text;
  document.getElementById('markSectionLabel').textContent = courseName + ' — ' + dateVal;

  const list = document.getElementById('markStudentList');
  list.innerHTML = '';

  if (!ALL_STUDENTS || ALL_STUDENTS.length === 0) {
    list.innerHTML = '<div class="empty-state"><i class="bi bi-people"></i><p>Student Not Found</p></div>';
  } else {
    ALL_STUDENTS.forEach(function(s) {
      const div = document.createElement('div');
      div.className = 'att-mark-row';
      div.innerHTML = `
        <div class="att-record-avatar" style="width:36px;height:36px;font-size:13px;margin-right:12px;flex-shrink:0;">${s.name[0].toUpperCase()}</div>
        <div style="flex:1;">
          <div style="font-weight:600;font-size:14px;">${s.name}</div>
          <div class="text-muted-sm">ID #${s.id}</div>
          <input type="hidden" name="student_ids" value="${s.id}"/>
        </div>
        <div class="d-flex gap-2">
          <label id="lP_${s.id}" class="att-radio-label att-present-lbl att-active">
            <input type="radio" name="status_${s.id}" value="present" id="p_${s.id}" style="display:none;" checked/> Present
          </label>
          <label id="lA_${s.id}" class="att-radio-label att-absent-lbl">
            <input type="radio" name="status_${s.id}" value="absent" id="a_${s.id}" style="display:none;"/> Absent
          </label>
        </div>`;
      div.querySelector('#lP_'+s.id).addEventListener('click', () => { document.getElementById('p_'+s.id).checked=true; syncStyle(s.id); });
      div.querySelector('#lA_'+s.id).addEventListener('click', () => { document.getElementById('a_'+s.id).checked=true; syncStyle(s.id); });
      list.appendChild(div);
    });
  }
  document.getElementById('markSection').style.display = 'block';
}

function syncStyle(sid) {
  const pChecked = document.getElementById('p_'+sid).checked;
  const lP = document.getElementById('lP_'+sid);
  const lA = document.getElementById('lA_'+sid);
  if (pChecked) { lP.classList.add('att-active'); lA.classList.remove('att-absent-active'); lA.classList.remove('att-active'); }
  else          { lA.classList.add('att-absent-active'); lP.classList.remove('att-active'); lA.classList.remove('att-active'); }
}

function markAll(status) {
  if (!ALL_STUDENTS) return;
  ALL_STUDENTS.forEach(s => {
    const el = document.getElementById((status === 'present' ? 'p_' : 'a_') + s.id);
    if (el) { el.checked = true; syncStyle(s.id); }
  });
}

// ═══════════════════════════════════════════════════════
//   STUDENT ATTENDANCE REPORT  (stu_attendence.html)
// ═══════════════════════════════════════════════════════

let activeRange    = 'month';
let customFromDate = null;
let customToDate   = null;

const RANGE_LABELS = {
  today:'Today', yesterday:'Yesterday', last7:'Last 7 Days',
  month:'This Month', lastmonth:'Last Month', lastyear:'Last Year', custom:'Custom Range'
};

function getDateRange(range) {
  const today = new Date(); today.setHours(0,0,0,0);
  let from, to = new Date(today);
  switch(range) {
    case 'today':     from = new Date(today); break;
    case 'yesterday': from = new Date(today); from.setDate(from.getDate()-1); to = new Date(from); break;
    case 'last7':     from = new Date(today); from.setDate(from.getDate()-6); break;
    case 'month':     from = new Date(today.getFullYear(), today.getMonth(), 1); break;
    case 'lastmonth': from = new Date(today.getFullYear(), today.getMonth()-1, 1); to = new Date(today.getFullYear(), today.getMonth(), 0); break;
    case 'lastyear':  from = new Date(today.getFullYear()-1, 0, 1); to = new Date(today.getFullYear()-1, 11, 31); break;
    case 'custom':
      from = customFromDate ? new Date(customFromDate) : new Date(today.getFullYear(), today.getMonth(), 1);
      to   = customToDate   ? new Date(customToDate)   : today; break;
    default: from = new Date(today.getFullYear(), today.getMonth(), 1);
  }
  return { from, to };
}

function toggleRangeDrop() {
  const drop  = document.getElementById('rangeDrop');
  const arrow = document.getElementById('rangeArrow');
  if (!drop) return;
  const open = drop.style.display !== 'none';
  drop.style.display = open ? 'none' : 'block';
  arrow.classList.toggle('open', !open);
}

function closeRangeDrop() {
  const drop  = document.getElementById('rangeDrop');
  const arrow = document.getElementById('rangeArrow');
  if (drop)  drop.style.display = 'none';
  if (arrow) arrow.classList.remove('open');
}

function selectRange(el) {
  document.querySelectorAll('.range-opt').forEach(o => o.classList.remove('active'));
  el.classList.add('active');
  activeRange = el.dataset.range;
  const customRow = document.getElementById('customRangeRow');
  if (customRow) customRow.classList.toggle('show', activeRange === 'custom');
}

function applyRange() {
  if (activeRange === 'custom') {
    customFromDate = document.getElementById('customFrom').value;
    customToDate   = document.getElementById('customTo').value;
    if (!customFromDate || !customToDate) { alert('Select both for the custom range'); return; }
  }
  const { from, to } = getDateRange(activeRange);
  const label         = fmtRangeLabel(from, to);
  const lbl = document.getElementById('rangeLabel');
  if (lbl) lbl.textContent = label;

  const tag  = document.getElementById('appliedRangeTag');
  const text = document.getElementById('appliedRangeText');
  if (tag && text) {
    text.textContent = RANGE_LABELS[activeRange] + ': ' + label;
    tag.style.display = 'block';
  }
  closeRangeDrop();
}

function generateReport() {
  const courseVal = document.getElementById('stuCourseSelect') ? document.getElementById('stuCourseSelect').value : '';
  const { from, to } = getDateRange(activeRange);
  const fromISO = isoDate(from);
  const toISO   = isoDate(to);

  if (typeof STU_RECORDS === 'undefined') return;

  let filtered = STU_RECORDS.filter(r => r.date >= fromISO && r.date <= toISO);
  if (courseVal !== '') filtered = filtered.filter(r => String(r.course_id) === String(courseVal));

  const subjectLabel = courseVal !== ''
    ? ((typeof STU_COURSE_MAP !== 'undefined') ? (STU_COURSE_MAP[courseVal] || 'Course #'+courseVal) : 'Course #'+courseVal)
    : 'All Subjects';
  const rangeLabel = fmtRangeLabel(from, to);

  const reportArea    = document.getElementById('reportArea');
  const reportNoData  = document.getElementById('reportNoData');
  const reportTableCard = document.getElementById('reportTableCard');

  if (reportArea)    reportArea.style.display    = 'block';
  if (reportNoData)  reportNoData.style.display  = 'none';
  if (reportTableCard) reportTableCard.style.display = 'none';

  // Update chips
  const setChip = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setChip('chipName',    typeof STU_USER_NAME !== 'undefined' ? STU_USER_NAME : '');
  setChip('chipSubject', subjectLabel);
  setChip('chipDate',    rangeLabel);

  if (filtered.length === 0) {
    const msgEl = document.getElementById('reportNoDataMsg');
    if (msgEl) msgEl.innerHTML = '<strong>' + rangeLabel + '</strong> No Record Found<br>Attendence Not Mark';
    if (reportNoData) reportNoData.style.display = 'block';
    const pct = document.getElementById('chipPct'); if (pct) { pct.textContent = '0%'; pct.style.color = '#ef4444'; }
    return;
  }

  // Build table
  const courseIds = courseVal !== '' ? [parseInt(courseVal)] : [...new Set(filtered.map(r => r.course_id))];
  const byDate = {};
  filtered.forEach(r => { if (!byDate[r.date]) byDate[r.date] = {}; byDate[r.date][r.course_id] = r.status; });

  const dates   = Object.keys(byDate).sort();
  const present = filtered.filter(r => r.status === 'present').length;
  const total   = filtered.length;
  const pct     = total > 0 ? Math.round((present/total)*100) : 0;

  const chipPct = document.getElementById('chipPct');
  if (chipPct) { chipPct.textContent = pct + '%'; chipPct.style.color = pct >= 75 ? '#10b981' : '#ef4444'; }

  const thead = document.getElementById('reportThead');
  const tbody = document.getElementById('reportTbody');
  const tfoot = document.getElementById('reportTfoot');
  if (!thead || !tbody || !tfoot) return;

  let headRow = '<tr><th>S.No.</th><th>Date</th>';
  courseIds.forEach(cid => {
    const cname = (typeof STU_COURSE_MAP !== 'undefined') ? (STU_COURSE_MAP[String(cid)] || 'Course #'+cid) : 'Course #'+cid;
    headRow += `<th>${cname}</th>`;
  });
  headRow += '<th>P</th><th>P+A</th><th>%</th></tr>';
  thead.innerHTML = headRow;

  let bodyHtml = ''; let totalPresent = 0, totalClasses = 0;
  dates.forEach((date, idx) => {
    const rowData = byDate[date]; let rowPresent = 0, rowTotal = 0; let cells = '';
    courseIds.forEach(cid => {
      const status = rowData[cid];
      if (status === 'present') { rowPresent++; rowTotal++; cells += `<td><span class="p-badge-present">P</span></td>`; }
      else if (status === 'absent') { rowTotal++; cells += `<td><span class="p-badge-absent">A</span></td>`; }
      else { cells += `<td style="color:var(--muted);">—</td>`; }
    });
    const rowPct = rowTotal > 0 ? Math.round((rowPresent/rowTotal)*100) : 0;
    const pctCls = rowPct >= 75 ? 'pct-high' : (rowPct >= 50 ? 'pct-mid' : 'pct-low');
    totalPresent += rowPresent; totalClasses += rowTotal;
    bodyHtml += `<tr><td style="color:var(--muted);">${idx+1}</td><td style="font-weight:500;">${fmtDate(date)}</td>${cells}<td><strong>${rowPresent}</strong></td><td>${rowTotal}</td><td class="${pctCls}">${rowPct}%</td></tr>`;
  });
  tbody.innerHTML = bodyHtml;

  const totalPct    = totalClasses > 0 ? Math.round((totalPresent/totalClasses)*100) : 0;
  const totalPctCls = totalPct >= 75 ? 'pct-high' : (totalPct >= 50 ? 'pct-mid' : 'pct-low');
  const footCells   = courseIds.map(() => '<td>—</td>').join('');
  tfoot.innerHTML = `<tr><td colspan="2" style="text-align:right;">Total:</td>${footCells}<td><strong>${totalPresent}</strong></td><td>${totalClasses}</td><td class="${totalPctCls}">${totalPct}%</td></tr>`;

  const reportTitle = document.getElementById('reportTitle'); if (reportTitle) reportTitle.innerHTML = '<i class="bi bi-table me-2" style="color:#3b82f6;"></i>Attendance Report';
  const reportSub   = document.getElementById('reportSub');   if (reportSub)   reportSub.textContent = (typeof STU_USER_NAME !== 'undefined' ? STU_USER_NAME : '') + ' — ' + subjectLabel;
  const reportCount = document.getElementById('reportCount'); if (reportCount) reportCount.textContent = dates.length + ' dates · ' + totalPresent + ' present / ' + totalClasses + ' total';
  if (reportTableCard) reportTableCard.style.display = 'block';
}

// Close range dropdown on outside click
document.addEventListener('click', function(e) {
  if (!e.target.closest('#rangeDrop') && !e.target.closest('.range-pill')) closeRangeDrop();
});

// ═══════════════════════════════════════════════════════
//   DOM READY
// ═══════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', function () {

  // Teacher attendance calendar
  if (document.getElementById('calStrip')) {
    selectedDate = todayISO();
    buildCalStrip();
    renderRecordsPanel();
  }

  // Init range label on student attendance page
  const rangeLabel = document.getElementById('rangeLabel');
  if (rangeLabel) {
    const { from, to } = getDateRange('month');
    rangeLabel.textContent = fmtRangeLabel(from, to);
  }

  // Auto-fill empty date inputs
  document.querySelectorAll('input[type="date"]').forEach(inp => { if (!inp.value) inp.value = todayISO(); });

  // Alert auto-hide
  document.querySelectorAll('.auto-hide-alert').forEach(el => {
    setTimeout(() => { el.style.transition='opacity 0.5s'; el.style.opacity='0'; setTimeout(() => el.remove(), 500); }, 3000);
  });

  // Bulk form submit spinner
  const bf = document.getElementById('bulkAttendanceForm');
  if (bf) {
    bf.addEventListener('submit', function() {
      const btn = bf.querySelector('button[type="submit"]');
      if (btn) { btn.disabled=true; btn.innerHTML='<span class="spinner-border spinner-border-sm me-2"></span>Submitting...'; }
    });
  }

  // Modal reset on close
  document.querySelectorAll('.modal').forEach(m => {
    m.addEventListener('hidden.bs.modal', () => {
      m.querySelectorAll('input:not([type=hidden]),textarea,select').forEach(inp => {
        if (inp.type !== 'radio' && inp.type !== 'checkbox') inp.value = '';
      });
    });
  });

  // Generic table search
  const si = document.getElementById('tableSearch');
  if (si) {
    si.addEventListener('input', function() {
      const q = this.value.toLowerCase();
      document.querySelectorAll('tbody tr').forEach(row => { row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none'; });
    });
  }

  // Submissions search (assigment.html)
  const subSearch = document.getElementById('subSearch');
  if (subSearch) {
    subSearch.addEventListener('input', function() {
      const q = this.value.toLowerCase();
      document.querySelectorAll('#submissionsPane tbody tr').forEach(row => { row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none'; });
    });
  }

  // Progress bar animate
  document.querySelectorAll('.progress-bar').forEach(bar => {
    const t = bar.style.width; bar.style.width = '0%';
    setTimeout(() => { bar.style.transition='width 1s ease'; bar.style.width=t; }, 200);
  });

});
// ═══════════════════════════════════════════════════════
//  TEACHER ATTENDANCE — Load Students into right panel
// ═══════════════════════════════════════════════════════

function teacherLoadStudents() {
  const assignVal = document.getElementById('markAssignSelect') 
                    ? document.getElementById('markAssignSelect').value
                    : (document.getElementById('markCourseSelect') ? document.getElementById('markCourseSelect').value : '');
  const dateVal  = document.getElementById('markDateInput').value;
  const errorDiv = document.getElementById('markError');

  errorDiv.style.display = 'none';

  if (!assignVal) {
    errorDiv.textContent   = '⚠️ Pehle Subject & Section select karo.';
    errorDiv.style.display = 'block';
    return;
  }
  if (!dateVal) {
    errorDiv.textContent   = '⚠️ Date select karo.';
    errorDiv.style.display = 'block';
    return;
  }

  // Parse subject_id:section_id or plain course_id
  const parts     = assignVal.split(':');
  const subjectId = parts[0];
  const sectionId = parts.length > 1 ? parts[1] : parts[0];

  // Set hidden form fields (new attendance form uses subject_id + section_id)
  if (document.getElementById('markFormSubjectId')) {
    document.getElementById('markFormSubjectId').value = subjectId;
    document.getElementById('markFormSectionId').value = sectionId;
  } else if (document.getElementById('markFormCourseId')) {
    document.getElementById('markFormCourseId').value  = subjectId;
  }
  document.getElementById('markFormDate').value = dateVal;

  // Get label for header
  const sel        = document.getElementById('markAssignSelect') || document.getElementById('markCourseSelect');
  const courseName = sel.options[sel.selectedIndex].text;

  // Update panel header
  document.getElementById('panelCourse').textContent = courseName;
  document.getElementById('panelDate').textContent   = 'Date: ' + dateVal;

  // Build student rows
  const list = document.getElementById('markStudentList');
  list.innerHTML = '';

  if (!ALL_STUDENTS || ALL_STUDENTS.length === 0) {
    list.innerHTML = '<div class="empty-state"><i class="bi bi-people"></i><p>Student not found</p></div>';
  } else {
    ALL_STUDENTS.forEach(function(s) {
      const div = document.createElement('div');
      div.className = 'att-mark-row';
      div.innerHTML = `
        <div class="att-record-avatar ta-student-avatar">${s.name[0].toUpperCase()}</div>
        <div class="ta-student-info">
          <div class="ta-student-name">${s.name}</div>
          <div class="ta-student-id">ID #${s.id}</div>
          <input type="hidden" name="student_ids" value="${s.id}"/>
        </div>
        <div class="ta-toggle-wrap">
          <label id="lP_${s.id}" class="att-radio-label att-present-lbl att-active">
            <input type="radio" name="status_${s.id}" value="present" id="p_${s.id}" style="display:none;" checked/>
             Present
          </label>
          <label id="lA_${s.id}" class="att-radio-label att-absent-lbl">
            <input type="radio" name="status_${s.id}" value="absent" id="a_${s.id}" style="display:none;"/>
             Absent
          </label>
        </div>`;

      div.querySelector('#lP_' + s.id).addEventListener('click', function() {
        document.getElementById('p_' + s.id).checked = true;
        teacherSyncStyle(s.id);
      });
      div.querySelector('#lA_' + s.id).addEventListener('click', function() {
        document.getElementById('a_' + s.id).checked = true;
        teacherSyncStyle(s.id);
      });

      list.appendChild(div);
    });
  }

  // Hide empty state, show mark panel
  document.getElementById('rightEmpty').style.display = 'none';
  document.getElementById('markPanel').style.display  = 'block';
}

function teacherSyncStyle(sid) {
  const pChecked = document.getElementById('p_' + sid).checked;
  const lP = document.getElementById('lP_' + sid);
  const lA = document.getElementById('lA_' + sid);
  if (pChecked) {
    lP.classList.add('att-active');
    lA.classList.remove('att-active');
    lA.classList.remove('att-absent-active');
  } else {
    lA.classList.add('att-absent-active');
    lP.classList.remove('att-active');
    lA.classList.remove('att-active');
  }
}

function teacherMarkAll(status) {
  if (!ALL_STUDENTS) return;
  ALL_STUDENTS.forEach(function(s) {
    const el = document.getElementById((status === 'present' ? 'p_' : 'a_') + s.id);
    if (el) { el.checked = true; teacherSyncStyle(s.id); }
  });
}
// ═══════════════════════════════════════════════════════
//   FILE UPLOAD ZONE  (notes.html)
// ═══════════════════════════════════════════════════════

(function initFileUpload() {
  document.addEventListener('DOMContentLoaded', function () {
    const fileInput  = document.getElementById('noteFile');
    const uploadZone = document.getElementById('uploadZone');
    const fileNameEl = document.getElementById('uploadFileName');

    if (!fileInput || !uploadZone) return;

    // Click on zone triggers file picker
    uploadZone.addEventListener('click', function () {
      fileInput.click();
    });

    // Show selected file name
    fileInput.addEventListener('change', function () {
      if (this.files && this.files[0]) {
        fileNameEl.textContent = '📎 ' + this.files[0].name;
        uploadZone.style.borderColor = 'var(--success)';
      } else {
        fileNameEl.textContent = '';
        uploadZone.style.borderColor = '';
      }
    });

    // Drag & drop support
    uploadZone.addEventListener('dragover', function (e) {
      e.preventDefault();
      uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', function () {
      uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', function (e) {
      e.preventDefault();
      uploadZone.classList.remove('dragover');
      const files = e.dataTransfer.files;
      if (files && files[0]) {
        fileInput.files = files;
        fileNameEl.textContent = '📎 ' + files[0].name;
        uploadZone.style.borderColor = 'var(--success)';
      }
    });
  });
})();
// ═══════════════════════════════════════════════════════
//  TEACHER ATTENDANCE — OVERWRITE teacherLoadStudents
//  (uses markAssignSelect with "subject_id:section_id")
// ═══════════════════════════════════════════════════════

// Override the old function defined above
teacherLoadStudents = function() {
  const assignSel = document.getElementById('markAssignSelect');
  const dateVal   = document.getElementById('markDateInput') ? document.getElementById('markDateInput').value : '';
  const errorDiv  = document.getElementById('markError');
  if (errorDiv) errorDiv.style.display = 'none';

  const assignVal = assignSel ? assignSel.value : '';
  if (!assignVal) {
    if (errorDiv) { errorDiv.textContent = '⚠️ Subject & Section select karo'; errorDiv.style.display = 'block'; }
    return;
  }
  if (!dateVal) {
    if (errorDiv) { errorDiv.textContent = '⚠️ Date select karo'; errorDiv.style.display = 'block'; }
    return;
  }

  const parts     = assignVal.split(':');
  const subjectId = parts[0] || '';
  const sectionId = parts[1] || '';
  const label     = assignSel.options[assignSel.selectedIndex].dataset.label ||
                    assignSel.options[assignSel.selectedIndex].text;

  const fSubject = document.getElementById('markFormSubjectId');
  const fSection = document.getElementById('markFormSectionId');
  const fDate    = document.getElementById('markFormDate');
  if (fSubject) fSubject.value = subjectId;
  if (fSection) fSection.value = sectionId;
  if (fDate)    fDate.value    = dateVal;

  const pCourse = document.getElementById('panelCourse');
  const pDate   = document.getElementById('panelDate');
  if (pCourse) pCourse.textContent = label;
  if (pDate)   pDate.textContent   = 'Date: ' + dateVal;

  const list = document.getElementById('markStudentList');
  if (list) {
    list.innerHTML = '';
    if (!ALL_STUDENTS || ALL_STUDENTS.length === 0) {
      list.innerHTML = '<div class="empty-state"><i class="bi bi-people"></i><p>No students found</p></div>';
    } else {
      ALL_STUDENTS.forEach(function(s) {
        const div = document.createElement('div');
        div.className = 'att-mark-row';
        div.innerHTML = `
          <div class="att-record-avatar ta-student-avatar">${s.name[0].toUpperCase()}</div>
          <div class="ta-student-info">
            <div class="ta-student-name">${s.name}</div>
            <div class="ta-student-id">ID #${s.id}</div>
            <input type="hidden" name="student_ids" value="${s.id}"/>
          </div>
          <div class="ta-toggle-wrap">
            <label id="lP_${s.id}" class="att-radio-label att-present-lbl att-active">
              <input type="radio" name="status_${s.id}" value="present" id="p_${s.id}" style="display:none;" checked/> Present
            </label>
            <label id="lA_${s.id}" class="att-radio-label att-absent-lbl">
              <input type="radio" name="status_${s.id}" value="absent" id="a_${s.id}" style="display:none;"/> Absent
            </label>
          </div>`;
        div.querySelector('#lP_' + s.id).addEventListener('click', function() {
          document.getElementById('p_' + s.id).checked = true;
          teacherSyncStyle(s.id);
        });
        div.querySelector('#lA_' + s.id).addEventListener('click', function() {
          document.getElementById('a_' + s.id).checked = true;
          teacherSyncStyle(s.id);
        });
        list.appendChild(div);
      });
    }
  }

  const rightEmpty = document.getElementById('rightEmpty');
  const markPanel  = document.getElementById('markPanel');
  if (rightEmpty) rightEmpty.style.display = 'none';
  if (markPanel)  markPanel.style.display  = 'block';
};

// ═══════════════════════════════════════════════════════
//  TEACHER ATTENDANCE — FILTER (Tab 2)
// ═══════════════════════════════════════════════════════

function teacherFilterAttendance() {
  const assignSel = document.getElementById('filterAssignSelect');
  const dateVal   = document.getElementById('filterDateInput') ? document.getElementById('filterDateInput').value : '';
  const resultCard = document.getElementById('filterResultCard');
  const resultTitle = document.getElementById('filterResultTitle');
  const resultCount = document.getElementById('filterResultCount');
  const resultBody  = document.getElementById('filterResultBody');

  const assignVal = assignSel ? assignSel.value : '';
  if (!assignVal) {
    if (resultBody) resultBody.innerHTML = '<div class="empty-state"><i class="bi bi-exclamation-circle"></i><p>Subject &amp; Section select karo</p></div>';
    return;
  }

  const parts     = assignVal.split(':');
  const subjectId = parts[0] || '0';
  const sectionId = parts[1] || '0';
  const label     = assignSel.options[assignSel.selectedIndex].text;

  // Show loading
  if (resultBody) resultBody.innerHTML = '<div style="text-align:center;padding:30px;color:var(--muted);"><span class="spinner-border spinner-border-sm me-2"></span>Loading...</div>';
  if (resultTitle) resultTitle.textContent = label + (dateVal ? ' — ' + dateVal : ' — All Dates');
  if (resultCount) { resultCount.style.display = 'none'; }

  const url = `/teacher/attendance/filter?subject_id=${subjectId}&section_id=${sectionId}&date=${dateVal}`;

  fetch(url)
    .then(r => r.json())
    .then(data => {
      const records = data.records || [];
      if (resultCount) {
        resultCount.textContent = records.length + ' record' + (records.length !== 1 ? 's' : '');
        resultCount.style.display = 'inline-block';
      }
      if (records.length === 0) {
        if (resultBody) resultBody.innerHTML = '<div class="empty-state"><i class="bi bi-calendar-x"></i><p>Is date/section ke liye koi record nahi</p></div>';
        return;
      }
      // Group by date
      const byDate = {};
      records.forEach(r => {
        if (!byDate[r.date]) byDate[r.date] = [];
        byDate[r.date].push(r);
      });
      const dates = Object.keys(byDate).sort().reverse();
      let html = '<div style="overflow-x:auto;padding:16px;"><table class="att-report-table"><thead><tr><th>#</th><th>Date</th><th>Student</th><th>Status</th></tr></thead><tbody>';
      let idx = 1;
      dates.forEach(date => {
        byDate[date].forEach(r => {
          const statusBadge = r.status === 'present'
            ? '<span class="p-badge-present">Present</span>'
            : '<span class="p-badge-absent">Absent</span>';
          html += `<tr><td style="color:var(--muted);">${idx++}</td><td style="font-weight:500;">${fmtDate(date)}</td><td>${r.student_name}</td><td>${statusBadge}</td></tr>`;
        });
      });
      const totalPresent = records.filter(r => r.status === 'present').length;
      const totalPct     = records.length > 0 ? Math.round((totalPresent / records.length) * 100) : 0;
      html += `</tbody><tfoot><tr><td colspan="3" style="text-align:right;font-weight:700;">Total Present:</td><td><strong>${totalPresent}/${records.length}</strong> <span style="color:${totalPct>=75?'#10b981':'#ef4444'};">(${totalPct}%)</span></td></tr></tfoot></table></div>`;
      if (resultBody) resultBody.innerHTML = html;
    })
    .catch(() => {
      if (resultBody) resultBody.innerHTML = '<div class="empty-state"><i class="bi bi-wifi-off"></i><p>Server se data load nahi hua. Dobara try karo.</p></div>';
    });
}
// ═══════════════════════════════════════════════════════
//  TEACHER ATTENDANCE — teacherLoadStudents
//  Uses markAssignSelect with "subject_id:section_id"
// ═══════════════════════════════════════════════════════
function teacherLoadStudents() {
  var assignSel = document.getElementById('markAssignSelect');
  var dateVal   = document.getElementById('markDateInput') ? document.getElementById('markDateInput').value : '';
  var errorDiv  = document.getElementById('markError');
  if (errorDiv) errorDiv.style.display = 'none';

  var assignVal = assignSel ? assignSel.value : '';
  if (!assignVal) {
    if (errorDiv) { errorDiv.textContent = '⚠️ Subject & Section select karo'; errorDiv.style.display = 'block'; }
    return;
  }
  if (!dateVal) {
    if (errorDiv) { errorDiv.textContent = '⚠️ Date select karo'; errorDiv.style.display = 'block'; }
    return;
  }

  var parts     = assignVal.split(':');
  var subjectId = parts[0] || '';
  var sectionId = parts[1] || '';
  var label     = assignSel.options[assignSel.selectedIndex].dataset.label
                  || assignSel.options[assignSel.selectedIndex].text;

  var fSubject = document.getElementById('markFormSubjectId');
  var fSection = document.getElementById('markFormSectionId');
  var fDate    = document.getElementById('markFormDate');
  if (fSubject) fSubject.value = subjectId;
  if (fSection) fSection.value = sectionId;
  if (fDate)    fDate.value    = dateVal;

  var pCourse = document.getElementById('panelCourse');
  var pDate   = document.getElementById('panelDate');
  if (pCourse) pCourse.textContent = label;
  if (pDate)   pDate.textContent   = 'Date: ' + dateVal;

  var list = document.getElementById('markStudentList');
  if (!list) return;
  list.innerHTML = '';

  if (!ALL_STUDENTS || ALL_STUDENTS.length === 0) {
    list.innerHTML = '<div class="empty-state"><i class="bi bi-people"></i><p>Is section mein koi student assign nahi hua.<br>Admin se students assign karwao.</p></div>';
  } else {
    ALL_STUDENTS.forEach(function(s) {
      var div = document.createElement('div');
      div.className = 'att-mark-row';
      div.innerHTML =
        '<div class="att-record-avatar ta-student-avatar">' + s.name[0].toUpperCase() + '</div>' +
        '<div class="ta-student-info">' +
          '<div class="ta-student-name">' + s.name + '</div>' +
          '<div class="ta-student-id">ID #' + s.id + '</div>' +
          '<input type="hidden" name="student_ids" value="' + s.id + '"/>' +
        '</div>' +
        '<div class="ta-toggle-wrap">' +
          '<label id="lP_' + s.id + '" class="att-radio-label att-present-lbl att-active">' +
            '<input type="radio" name="status_' + s.id + '" value="present" id="p_' + s.id + '" style="display:none;" checked/> Present' +
          '</label>' +
          '<label id="lA_' + s.id + '" class="att-radio-label att-absent-lbl">' +
            '<input type="radio" name="status_' + s.id + '" value="absent" id="a_' + s.id + '" style="display:none;"/> Absent' +
          '</label>' +
        '</div>';
      var lP = div.querySelector('#lP_' + s.id);
      var lA = div.querySelector('#lA_' + s.id);
      lP.addEventListener('click', function() { document.getElementById('p_' + s.id).checked = true; teacherSyncStyle(s.id); });
      lA.addEventListener('click', function() { document.getElementById('a_' + s.id).checked = true; teacherSyncStyle(s.id); });
      list.appendChild(div);
    });
  }

  var rightEmpty = document.getElementById('rightEmpty');
  var markPanel  = document.getElementById('markPanel');
  if (rightEmpty) rightEmpty.style.display = 'none';
  if (markPanel)  markPanel.style.display  = 'block';
}

function teacherSyncStyle(sid) {
  var pChecked = document.getElementById('p_' + sid).checked;
  var lP = document.getElementById('lP_' + sid);
  var lA = document.getElementById('lA_' + sid);
  if (pChecked) {
    lP.classList.add('att-active');
    lA.classList.remove('att-active', 'att-absent-active');
  } else {
    lA.classList.add('att-absent-active');
    lP.classList.remove('att-active');
    lA.classList.remove('att-active');
  }
}

function teacherMarkAll(status) {
  if (!ALL_STUDENTS) return;
  ALL_STUDENTS.forEach(function(s) {
    var el = document.getElementById((status === 'present' ? 'p_' : 'a_') + s.id);
    if (el) { el.checked = true; teacherSyncStyle(s.id); }
  });
}

// ═══════════════════════════════════════════════════════
//  VIEW ATTENDANCE MODAL — loadAttendanceView()
// ═══════════════════════════════════════════════════════
function loadAttendanceView() {
  var assignSel = document.getElementById('viewAssignSelect');
  var dateVal   = document.getElementById('viewDateInput') ? document.getElementById('viewDateInput').value : '';
  var resultDiv = document.getElementById('viewAttResult');

  var assignVal = assignSel ? assignSel.value : '';
  if (!assignVal) {
    if (resultDiv) resultDiv.innerHTML = '<div class="empty-state" style="padding:20px 0;"><i class="bi bi-exclamation-circle"></i><p>Subject &amp; Section select karo</p></div>';
    return;
  }

  var parts     = assignVal.split(':');
  var subjectId = parts[0] || '0';
  var sectionId = parts[1] || '0';

  if (resultDiv) resultDiv.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted);"><span class="spinner-border spinner-border-sm me-2"></span>Loading...</div>';

  var url = '/teacher/attendance/view?subject_id=' + subjectId + '&section_id=' + sectionId + '&date=' + dateVal;

  fetch(url)
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var records = data.records || [];
      if (records.length === 0) {
        resultDiv.innerHTML = '<div class="empty-state" style="padding:24px 0;"><i class="bi bi-calendar-x"></i><p>Is selection ke liye koi attendance record nahi mila.</p></div>';
        return;
      }
      var totalPresent = records.filter(function(r){ return r.status === 'present'; }).length;
      var totalPct     = records.length > 0 ? Math.round((totalPresent / records.length) * 100) : 0;
      var pctColor     = totalPct >= 75 ? '#10b981' : '#ef4444';

      var html = '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px;">' +
        '<span style="background:rgba(16,185,129,0.12);color:#10b981;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700;">' +
          '✅ Present: ' + totalPresent + '</span>' +
        '<span style="background:rgba(239,68,68,0.12);color:#ef4444;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700;">' +
          '❌ Absent: ' + (records.length - totalPresent) + '</span>' +
        '<span style="background:rgba(59,130,246,0.12);color:#3b82f6;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700;">' +
          '📊 Total: ' + records.length + '</span>' +
        '<span style="background:rgba(129,140,248,0.12);color:' + pctColor + ';padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700;">' +
          '% ' + totalPct + '%</span>' +
        '</div>';

      html += '<div style="overflow-x:auto;"><table class="att-report-table">' +
        '<thead><tr><th>#</th><th>Student</th><th>Date</th><th>Status</th></tr></thead><tbody>';

      records.forEach(function(r, idx) {
        var badge = r.status === 'present'
          ? '<span class="p-badge-present">Present</span>'
          : '<span class="p-badge-absent">Absent</span>';
        html += '<tr><td style="color:var(--muted);">' + (idx + 1) + '</td>' +
          '<td><strong>' + r.student_name + '</strong></td>' +
          '<td>' + fmtDate(r.date) + '</td>' +
          '<td>' + badge + '</td></tr>';
      });

      html += '</tbody></table></div>';
      resultDiv.innerHTML = html;
    })
    .catch(function() {
      resultDiv.innerHTML = '<div class="empty-state" style="padding:20px 0;"><i class="bi bi-wifi-off"></i><p>Data load nahi hua. Dobara try karo.</p></div>';
    });
}

// ═══════════════════════════════════════════════════════
//  FILE UPLOAD ZONE  (notes.html)
// ═══════════════════════════════════════════════════════
(function initFileUpload() {
  document.addEventListener('DOMContentLoaded', function () {
    var fileInput  = document.getElementById('noteFile');
    var uploadZone = document.getElementById('uploadZone');
    var fileNameEl = document.getElementById('uploadFileName');
    if (!fileInput || !uploadZone) return;

    uploadZone.addEventListener('click', function () { fileInput.click(); });

    fileInput.addEventListener('change', function () {
      if (this.files && this.files[0]) {
        if (fileNameEl) fileNameEl.textContent = '📎 ' + this.files[0].name;
        uploadZone.style.borderColor = 'var(--accent)';
      } else {
        if (fileNameEl) fileNameEl.textContent = '';
        uploadZone.style.borderColor = '';
      }
    });

    uploadZone.addEventListener('dragover', function (e) {
      e.preventDefault(); uploadZone.classList.add('dragover');
    });
    uploadZone.addEventListener('dragleave', function () {
      uploadZone.classList.remove('dragover');
    });
    uploadZone.addEventListener('drop', function (e) {
      e.preventDefault(); uploadZone.classList.remove('dragover');
      var files = e.dataTransfer.files;
      if (files && files[0]) {
        fileInput.files = files;
        if (fileNameEl) fileNameEl.textContent = '📎 ' + files[0].name;
        uploadZone.style.borderColor = 'var(--accent)';
      }
    });
  });
})();