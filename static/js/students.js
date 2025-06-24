/**
 * students.js
 *  – перемикає призначення пісні учню по чекбоксу
 *  – он‑лайн оновлює зведену таблицю «Вивчені твори»
 */

document.addEventListener("DOMContentLoaded", () => {
  /* ---- службові словники ---- */
  const songTitles = JSON.parse(
    document.getElementById("song-titles").textContent
  );

  /** Оновити рядок зведеної таблиці для конкретного учня */
  function updateSummaryRow(studentId) {
    const checked = document.querySelectorAll(
      `#assign-table tr[data-sid="${studentId}"] input.assign-box:checked`
    );
    const titles = Array.from(checked, (cb) => songTitles[cb.dataset.tid]);
    const cell = document.querySelector(
      `#summary-table tr[data-sid="${studentId}"] .songs-list`
    );
    cell.textContent = titles.join(", ");
  }

  /** Відправити на бекенд assign / unassign  і після успіху оновити таблицю */
  async function toggleAssign(ev) {
    const box = ev.currentTarget;
    const studentId = box.dataset.sid;
    const songId = box.dataset.tid;
    const url = box.checked
      ? "/api/assign"
      : `/api/unassign/${studentId}/${songId}`;
    const options = box.checked
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ student_id: studentId, song_id: songId })
        }
      : { method: "DELETE" };

    box.disabled = true;
    try {
      const r = await fetch(url, options);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      updateSummaryRow(studentId);
    } catch (err) {
      alert("Помилка збереження! Спробуйте пізніше.");
      box.checked = !box.checked; // повертаємо стан назад
    } finally {
      box.disabled = false;
    }
  }

  /** Навісити слухачів на всі чекбокси */
  document.querySelectorAll("input.assign-box").forEach((box) => {
    box.addEventListener("change", toggleAssign);
  });
});
