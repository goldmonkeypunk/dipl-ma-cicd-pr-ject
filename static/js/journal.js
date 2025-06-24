document.addEventListener("DOMContentLoaded", () => {
  const pricePerLesson = 130;           // лише для відображення (бекенд рахує сам)

  /** Оновити комірку «сума» конкретного учня та загальний підсумок */
  function updateSums(rowElem, newRowSum, newTotal) {
    rowElem.querySelector(".sum").textContent = newRowSum;
    document.getElementById("grand-total").textContent = newTotal;
  }

  /** Обробник кліку по чекбоксу */
  async function toggleAttendance(ev) {
    const cb   = ev.currentTarget;
    const row  = cb.closest("tr");
    const body = {
      student_id: row.dataset.student,
      date: cb.dataset.date
    };

    cb.disabled = true;                 // короткий захист від «двійного» кліку

    try {
      const r = await fetch("/api/attendance/toggle", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
      });

      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      updateSums(row, data.month_sum, data.total);
    } catch (err) {
      alert("Помилка збереження. Спробуйте ще раз.");
      // повертаємо чекбокс у попередній стан
      cb.checked = !cb.checked;
    } finally {
      cb.disabled = false;
    }
  }

  /** Навішуємо слухачів на усі чекбокси таблиці */
  document.querySelectorAll("input.attend").forEach(cb => {
    cb.addEventListener("change", toggleAttendance);
  });
});
