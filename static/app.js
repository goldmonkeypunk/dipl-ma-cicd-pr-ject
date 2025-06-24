document.addEventListener("DOMContentLoaded", () => {
    // Оновити підсумковий рядок для учня (список призначених пісень)
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

    /** Відправити на бекенд запит (assign чи unassign) і після успіху оновити таблицю */
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
            box.checked = !box.checked;  // повертаємо стан назад у разі помилки
        } finally {
            box.disabled = false;
        }
    }

    /** Навісити обробники на всі чекбокси призначення пісень */
    document.querySelectorAll("input.assign-box").forEach((box) => {
        box.addEventListener("change", toggleAssign);
    });
});/* global fetch */

document.addEventListener("DOMContentLoaded", () => {

  /* ───────── Journal click ───────── */
  document.querySelectorAll(".att").forEach(td => {
    if (!td.dataset.stu) return;
    td.addEventListener("click", async () => {
      const r = await fetch("/api/attendance/toggle", {
        method : "POST",
        headers: { "Content-Type": "application/json" },
        body   : JSON.stringify({ student_id: td.dataset.stu,
                                  date      : td.dataset.date })
      });
      if (!r.ok) return;
      const j = await r.json();
      td.classList.toggle("table-success");
      td.innerText = td.classList.contains("table-success") ? "✓" : "";
      td.parentElement.querySelector(".month-sum").innerText = j.month_sum;
      document.getElementById("total").innerText             = j.total;
    });
  });

  /* ───────── Add Student ───────── */
  const addStudent = document.getElementById("addStudent");
  if (addStudent){
    addStudent.addEventListener("submit", async e => {
      e.preventDefault();
      const name = addStudent.elements.name.value.trim();
      if (!name) return;
      const r = await fetch("/api/student", {
        method:"POST", headers:{'Content-Type':'application/json'},
        body:JSON.stringify({name})
      });
      if (r.ok) location.reload();
    });
  }

  /* ───────── Delete Student ───────── */
  document.querySelectorAll(".del-stu").forEach(btn=>{
    btn.addEventListener("click", async ()=>{
      if(!confirm("Видалити учня разом із відвідуваністю?")) return;
      const id=btn.dataset.id;
      const r = await fetch(`/api/student/${id}`,{method:"DELETE"});
      if(r.ok){
        document.getElementById(`stu-${id}`)?.remove();
        document.getElementById(`row-${id}`)?.remove();
      }
    });
  });

  /* ───────── Add Song ───────── */
  const addSong = document.getElementById("addSong");
  if (addSong){
    addSong.addEventListener("submit", async e => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(addSong));
      const r = await fetch("/api/song", {
        method:"POST", headers:{'Content-Type':'application/json'},
        body:JSON.stringify(data)
      });
      if (r.ok) location.reload();
    });
  }

  /* ───────── Delete Song ───────── */
  document.querySelectorAll(".del-song").forEach(btn=>{
    btn.addEventListener("click", async ()=>{
      if(!confirm("Видалити пісню з каталогу?")) return;
      const id=btn.dataset.id;
      const r = await fetch(`/api/song/${id}`,{method:"DELETE"});
      if(r.ok) document.getElementById(`song-${id}`)?.remove();
    });
  });

  /* ───────── Assign Song ───────── */
  document.querySelectorAll(".song-select").forEach(sel => {
    sel.addEventListener("change", async () => {
      const sid = sel.dataset.stu;
      const tid = sel.value;
      if (!(sid && tid)) return;
      await fetch("/api/assign", {
        method : "POST",
        headers: { "Content-Type": "application/json" },
        body   : JSON.stringify({ student_id: sid, song_id: tid })
      });
      sel.selectedIndex = 0;
    });
  });

});
