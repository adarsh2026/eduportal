// ═══════════════════════════════════════════════
//   EduPortal — app.js  (sabka JS yahan hai)
// ═══════════════════════════════════════════════

// ── 1. Notes Download (Student) ──────────────────
function downloadNote(title, content) {
  const blob = new Blob([content], { type: 'text/plain' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = title.replace(/\s+/g, '_') + '.txt';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

// ── 2. Delete Confirm (Admin – Teachers/Students) ─
function confirmDelete(name) {
  return confirm('Are you sure you want to delete "' + name + '"?');
}

// ── 3. Attendance Form Validation ────────────────
document.addEventListener('DOMContentLoaded', function () {

  // Auto-set today's date on attendance date inputs
  const dateInputs = document.querySelectorAll('input[type="date"]');
  dateInputs.forEach(function (input) {
    if (!input.value) {
      const today = new Date().toISOString().split('T')[0];
      input.value = today;
    }
  });

  // ── 4. Toast / Alert auto-hide ──────────────────
  const alerts = document.querySelectorAll('.auto-hide-alert');
  alerts.forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 500);
    }, 3000);
  });

  // ── 5. Sidebar active link highlight ────────────
  const links    = document.querySelectorAll('.nav-link');
  const current  = window.location.pathname;
  links.forEach(function (link) {
    if (link.getAttribute('href') === current) {
      link.classList.add('active');
    }
  });

  // ── 6. Assignment submit button loading state ───
  const submitBtns = document.querySelectorAll('form .btn-primary');
  submitBtns.forEach(function (btn) {
    btn.closest('form') && btn.closest('form').addEventListener('submit', function () {
      btn.disabled    = true;
      btn.innerHTML   = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
    });
  });

  // ── 7. Modal reset on close ─────────────────────
  const modals = document.querySelectorAll('.modal');
  modals.forEach(function (modal) {
    modal.addEventListener('hidden.bs.modal', function () {
      const inputs = modal.querySelectorAll('input:not([type=hidden]), textarea, select');
      inputs.forEach(function (input) {
        if (input.type !== 'radio' && input.type !== 'checkbox') {
          input.value = '';
        }
      });
    });
  });

  // ── 8. Attendance mark — bulk submit all students ─
  const bulkForm = document.getElementById('bulkAttendanceForm');
  if (bulkForm) {
    bulkForm.addEventListener('submit', function (e) {
      const radios = bulkForm.querySelectorAll('input[type="radio"]:checked');
      if (radios.length === 0) {
        e.preventDefault();
        alert('Please select status for at least one student.');
      }
    });
  }

  // ── 9. Table search / filter ─────────────────────
  const searchInput = document.getElementById('tableSearch');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      const q    = this.value.toLowerCase();
      const rows = document.querySelectorAll('tbody tr');
      rows.forEach(function (row) {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
      });
    });
  }

  // ── 10. Progress bar animate on load ─────────────
  const bars = document.querySelectorAll('.progress-bar');
  bars.forEach(function (bar) {
    const target = bar.style.width;
    bar.style.width = '0%';
    setTimeout(function () {
      bar.style.transition = 'width 1s ease';
      bar.style.width = target;
    }, 200);
  });

});