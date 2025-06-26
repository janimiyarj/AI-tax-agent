// form-logic.js

// Toggle itemized fields visibility
function toggleItemized(show) {
  const fields = document.getElementById('itemized_fields');
  if (fields) {
    fields.style.display = show ? 'block' : 'none';
  }
}

// Autofill zero if left empty (optional)
document.addEventListener("DOMContentLoaded", () => {
  const numericFields = document.querySelectorAll('input[type="number"]');
  numericFields.forEach(input => {
    input.addEventListener('blur', () => {
      if (input.value === '') {
        input.value = 0;
      }
    });
  });
});
