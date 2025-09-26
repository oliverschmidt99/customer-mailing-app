// static/js/kontakt_editor.js

document.addEventListener("DOMContentLoaded", function () {
  // Daten aus den JSON-Skriptblöcken auslesen
  const selectionOptionsRaw = document.getElementById("selection-options-data");
  const selectionOptions = selectionOptionsRaw
    ? JSON.parse(selectionOptionsRaw.textContent)
    : {};

  // FIX: Lese die Kontakt ID aus dem JSON Block
  const contactIdRaw = document.getElementById("contact-id-data");
  const existingContactId = contactIdRaw
    ? JSON.parse(contactIdRaw.textContent)
    : null;

  // Element-Referenzen
  const attributesContainer = document.getElementById("kontakt_attributes");
  const addAttributeBtn = document.getElementById("addAttributeBtn");

  // --- MODAL-ELEMENTE ---
  const modal = document.getElementById("selectOptionModal");
  const closeBtn = modal.querySelector(".modal-close-btn");
  const optionsList = document.getElementById("modal-options-list");
  const newOptionInput = document.getElementById("newOptionInput");
  const addOptionBtn = document.getElementById("addOptionBtn");
  const saveOptionsBtn = document.getElementById("saveOptionsBtn");
  const modalKeyTitle = document.getElementById("modal-key-title");
  let currentSelectElement = null;
  let currentKey = null;

  // --- HELPER-FUNKTIONEN ---

  // Funktion, die den DOM-Knoten für ein Select-Feld erstellt
  function createSelectField(key, value) {
    const wrapper = document.createElement("div");
    wrapper.className = "attribute-field";

    const label = document.createElement("label");
    label.textContent = key;
    wrapper.appendChild(label);

    const inputGroup = document.createElement("div");
    inputGroup.className = "select-group input-group";

    const select = document.createElement("select");
    select.name = `attribute_value_${key}`;
    select.className = "attribute-input select-input input-field";

    // Optionen füllen
    const options = selectionOptions[key] || [];
    select.innerHTML = '<option value="">(Bitte wählen)</option>';
    options.forEach((option) => {
      const optionElement = document.createElement("option");
      optionElement.value = option;
      optionElement.textContent = option;
      if (option === value) {
        optionElement.selected = true;
      }
      select.appendChild(optionElement);
    });

    // Verstecktes Feld für den Key
    const hiddenKeyInput = document.createElement("input");
    hiddenKeyInput.type = "hidden";
    hiddenKeyInput.name = `attribute_key_${key}`;
    hiddenKeyInput.value = key;

    // Edit-Button
    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.className = "icon-btn edit";
    editButton.innerHTML = `<img src="${window.location.origin}/static/img/icon_edit.svg" alt="Bearbeiten">`;
    editButton.title = "Optionen bearbeiten";
    editButton.addEventListener("click", (e) => {
      e.preventDefault();
      openModal(key, select);
    });

    // Delete-Button
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "delete-attribute icon-btn delete";
    deleteButton.innerHTML = `<img src="${window.location.origin}/static/img/icon_delete.svg" alt="Entfernen">`;
    deleteButton.addEventListener("click", function () {
      this.closest(".attribute-field").remove();
    });

    inputGroup.appendChild(select);
    inputGroup.appendChild(editButton);
    inputGroup.appendChild(deleteButton);

    wrapper.appendChild(inputGroup);
    wrapper.appendChild(hiddenKeyInput);

    return wrapper;
  }

  // Funktion, die den DOM-Knoten für ein Text-Feld erstellt
  function createTextField(key, value) {
    const wrapper = document.createElement("div");
    wrapper.className = "attribute-field";

    const label = document.createElement("label");
    label.textContent = key;
    wrapper.appendChild(label);

    const inputGroup = document.createElement("div");
    inputGroup.className = "input-group";

    // Key-Input
    const keyInput = document.createElement("input");
    keyInput.type = "text";
    keyInput.name = `attribute_key_${key}`;
    keyInput.value = key;
    keyInput.placeholder = "Attributname";
    keyInput.className = "attribute-key-input input-field";

    // Wert-Input
    const valueInput = document.createElement("input");
    valueInput.type = "text";
    valueInput.name = `attribute_value_${key}`;
    valueInput.value = value;
    valueInput.placeholder = "Wert";
    valueInput.className = "attribute-input input-field";

    // Delete-Button
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "delete-attribute icon-btn delete";
    deleteButton.innerHTML = `<img src="${window.location.origin}/static/img/icon_delete.svg" alt="Entfernen">`;
    deleteButton.addEventListener("click", function () {
      this.closest(".attribute-field").remove();
    });

    inputGroup.appendChild(keyInput);
    inputGroup.appendChild(valueInput);
    inputGroup.appendChild(deleteButton);
    wrapper.appendChild(inputGroup);

    return wrapper;
  }

  // Funktion, die das Attribut-Feld basierend auf dem Typ erstellt
  function createAttributeField(key = "Neues Attribut", value = "") {
    // Prüfe, ob es vordefinierte Optionen gibt
    if (selectionOptions[key] && selectionOptions[key].length > 0) {
      return createSelectField(key, value);
    }

    // Ansonsten Standard-Textfeld
    return createTextField(key, value);
  }

  // Initialisierung der vorhandenen Attribute beim Laden
  attributesContainer.querySelectorAll(".attribute-field").forEach((field) => {
    const keyInput = field.querySelector(".attribute-key-input");
    const valueInput = field.querySelector(".attribute-input");

    if (keyInput && valueInput) {
      const key = keyInput.value;
      const value = valueInput.value;

      if (selectionOptions[key] && selectionOptions[key].length > 0) {
        const newField = createSelectField(key, value);
        field.replaceWith(newField);
      }
    }
  });

  // Event Listener für "Attribut hinzufügen"
  addAttributeBtn.addEventListener("click", function () {
    // Suche den nächsten freien Namen, z.B. Attribut 1, Attribut 2
    let newKey = "Neues Attribut";
    let counter = 1;
    while (document.querySelector(`[name="attribute_key_${newKey}"]`)) {
      newKey = `Attribut ${counter}`;
      counter++;
    }

    const newField = createAttributeField(newKey, "");
    attributesContainer.appendChild(newField);
  });

  // --- MODAL-LOGIK ---

  function openModal(key, selectElement) {
    currentKey = key;
    currentSelectElement = selectElement;

    // Setze den h3-Titel im Modal
    modalKeyTitle.textContent = `Optionen für: ${key}`;
    optionsList.innerHTML = "";

    const options = selectionOptions[key] || [];
    options.forEach((option) => addOptionToModal(option));

    modal.style.display = "flex";
    newOptionInput.value = "";
  }

  // Die Funktion closeModal ist nun global im HTML definiert
  // function closeModal() { ... }

  function addOptionToModal(optionText) {
    const li = document.createElement("li");
    li.textContent = optionText;

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "delete-option-btn icon-btn delete";
    deleteBtn.innerHTML = `<img src="${window.location.origin}/static/img/icon_delete.svg" alt="Entfernen">`;
    deleteBtn.addEventListener("click", function (e) {
      e.preventDefault();
      li.remove();
    });

    li.appendChild(deleteBtn);
    optionsList.appendChild(li);
  }

  // Schließen des Modals
  if (closeBtn) closeBtn.onclick = closeModal;
  window.onclick = function (event) {
    if (event.target == modal) {
      closeModal();
    }
  };

  // Option hinzufügen
  addOptionBtn.addEventListener("click", function (e) {
    e.preventDefault();
    const newOption = newOptionInput.value.trim();
    if (newOption) {
      const existing = Array.from(optionsList.querySelectorAll("li")).map(
        (li) => li.childNodes[0].textContent.trim()
      );
      if (!existing.includes(newOption)) {
        addOptionToModal(newOption);
      }
      newOptionInput.value = "";
    }
  });

  // Optionen speichern
  saveOptionsBtn.addEventListener("click", function (e) {
    e.preventDefault();
    const newOptions = Array.from(optionsList.querySelectorAll("li")).map(
      (li) => li.childNodes[0].textContent.trim()
    );

    if (currentKey) {
      // 1. Im Frontend speichern
      selectionOptions[currentKey] = newOptions;

      // 2. Select-Feld im Editor aktualisieren
      const currentValue = currentSelectElement.value;
      currentSelectElement.innerHTML =
        '<option value="">(Bitte wählen)</option>';
      newOptions.forEach((option) => {
        const optionElement = document.createElement("option");
        optionElement.value = option;
        optionElement.textContent = option;
        if (option === currentValue) {
          optionElement.selected = true;
        }
        currentSelectElement.appendChild(optionElement);
      });
    }

    closeModal();
  });

  // --- KONTAKT-VERKNÜPFUNG (Autocomplete-Logik) ---

  const verknuepfungSelect = document.getElementById("new_verknuepfung_select");
  const verknuepfungGroup = document.getElementById("verknuepfung-group");
  const searchInput = document.getElementById("autocomplete-search-input");

  // Event Listener für die Suche
  searchInput.addEventListener("input", function () {
    const query = this.value;
    fetchVerknuepfungsOptions(query);
    verknuepfungSelect.style.display = query.length >= 2 ? "block" : "none";
  });

  // Event Listener für Auswahl im Dropdown
  verknuepfungSelect.addEventListener("change", function () {
    const selectedId = this.value;
    const selectedText = this.options[this.selectedIndex].text;

    if (selectedId) {
      addVerknuepfungDOM(selectedId, selectedText);

      // Setze Suchfeld und Select zurück
      searchInput.value = "";
      verknuepfungSelect.innerHTML =
        '<option value="">Nach Kontakt suchen...</option>';
      verknuepfungSelect.style.display = "none";
    }
  });

  // AJAX-Funktion zur Kontaktsuche
  function fetchVerknuepfungsOptions(query) {
    if (query.length < 2) {
      verknuepfungSelect.innerHTML =
        '<option value="">Nach Kontakt suchen...</option>';
      return;
    }

    // Verwende den korrekten Endpunkt: /kontakte/api/kontakte/search
    fetch(
      `/kontakte/api/kontakte/search?q=${encodeURIComponent(query)}&limit=10`
    )
      .then((response) => response.json())
      .then((data) => {
        verknuepfungSelect.innerHTML =
          '<option value="">Nach Kontakt suchen...</option>';
        data.forEach((kontakt) => {
          if (kontakt.id != existingContactId) {
            const option = document.createElement("option");
            option.value = kontakt.id;
            option.textContent = kontakt.text;
            verknuepfungSelect.appendChild(option);
          }
        });
      })
      .catch((error) => console.error("Fehler bei der Kontaktsuche:", error));
  }

  // Hilfsfunktion: Fügt eine Verknüpfung zur DOM hinzu
  function addVerknuepfungDOM(id, text) {
    const idInt = parseInt(id);

    // Überprüfen, ob die Verknüpfung bereits existiert
    const existingInputs = verknuepfungGroup.querySelectorAll(
      `input[name="verknuepfung_ids"][value="${idInt}"]`
    );
    if (existingInputs.length > 0 || idInt == existingContactId) {
      alert(
        "Dieser Kontakt ist bereits verknüpft oder ist der aktuelle Kontakt."
      );
      return;
    }

    const placeholderDiv = searchInput.closest(".attribute-field");

    const newField = document.createElement("div");
    newField.className = "attribute-field";
    newField.innerHTML = `
            <label>Verknüpfung</label>
            <div class="verknuepfung-select-container">
                <input type="hidden" name="verknuepfung_ids" value="${idInt}">
                <input type="text" 
                       class="verknuepfung-display-input input-field" 
                       value="${text}" 
                       readonly>
                <button type="button" class="delete-attribute icon-btn delete" onclick="removeVerknuepfung(this)">
                    <img src="${window.location.origin}/static/img/icon_delete.svg" alt="Entfernen">
                </button>
            </div>
        `;

    verknuepfungGroup.insertBefore(newField, placeholderDiv);
  }
});
