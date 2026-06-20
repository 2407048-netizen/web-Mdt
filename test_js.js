// Dynamic classroom filtering based on chosen prayer session
function updateClassrooms() {
    const sessionSelect = { value: "Magrib" };
    const classSelect = { innerHTML: "", value: "16", appendChild: () => {} };
    
    if (!sessionSelect || !classSelect) return;
    
    const selectedSession = sessionSelect.value;
    const sessionClassrooms = {"Ashar": [{"id": 5, "name": "Ashar 1"}, {"id": 6, "name": "Ashar 2"}, {"id": 7, "name": "Ashar 3"}], "Dzuhur": [{"id": 4, "name": "Dzuhur 1"}], "Magrib": [{"id": 8, "name": "Magrib 1"}, {"id": 9, "name": "Magrib 2"}, {"id": 10, "name": "Magrib 3"}, {"id": 11, "name": "Magrib 4"}, {"id": 12, "name": "Magrib 5"}, {"id": 13, "name": "Magrib 6"}, {"id": 14, "name": "Magrib 7"}, {"id": 15, "name": "Magrib 8"}, {"id": 16, "name": "Magrib 9"}], "Subuh": [{"id": 1, "name": "Subuh 1"}, {"id": 2, "name": "Subuh 2"}, {"id": 3, "name": "Subuh 3"}]};
    const currentSelected = classSelect.value || "16";

    // Clear class options
    classSelect.innerHTML = '<option value="">— Pilih Kelas —</option>';
    
    // Fallback to all classes flat array
    const allClassrooms = [];
    Object.keys(sessionClassrooms).forEach(function(k) {
        if (sessionClassrooms[k]) {
            sessionClassrooms[k].forEach(function(c) {
                allClassrooms.push(c);
            });
        }
    });

    const classList = (selectedSession && sessionClassrooms[selectedSession])
        ? sessionClassrooms[selectedSession]
        : allClassrooms;

    let matched = false;
    classList.forEach(function(cls) {
        const opt = { value: cls.id, textContent: cls.name };
        if (String(cls.id) === String(currentSelected)) {
            opt.selected = true;
            matched = true;
        }
        classSelect.appendChild(opt);
    });

    if (selectedSession && !matched) {
        classSelect.value = "";
    }
}

// Click avatar to trigger file input
function triggerPhotoUpload() {
}

// Live image previewer
function previewImage(event) {
}

// Live username update to display name
const inputUsername = { addEventListener: () => {} };
const profileDisplayName = { textContent: "" };

if (inputUsername && profileDisplayName) {
    inputUsername.addEventListener('input', function() {
    });
}

function syncSubjectRows() {
    const checkboxes = [{ value: "0", checked: true }];
    let visibleCount = 0;
    
    checkboxes.forEach(cb => {
        const dayIdx = cb.value;
        const row = { style: { display: "" }, querySelector: () => ({ setAttribute: () => {}, removeAttribute: () => {} }) };
        if (!row) return;
        
        const input = row.querySelector(`input[name="subject_book_${dayIdx}"]`);
        
        if (cb.checked) {
            row.style.display = 'flex';
            if (input) input.setAttribute('required', 'required');
            visibleCount++;
        } else {
            row.style.display = 'none';
            if (input) input.removeAttribute('required');
        }
    });
}

syncSubjectRows();
updateClassrooms();
console.log("Syntax is 100% correct!");
