document.addEventListener("DOMContentLoaded", () => {
  const appRoot = document.getElementById("kontakte-app");
  if (!appRoot) {
    return;
  }

  const { createApp, ref, computed, watch, nextTick } = Vue;

  const app = createApp({
    setup() {
      // --- Kompletter State ---
      const vorlagen = ref(
        JSON.parse(
          document.getElementById("vorlagen-for-json-data").textContent
        )
      );
      const activeVorlageId = ref(
        vorlagen.value.length > 0 ? vorlagen.value[0].id : null
      );
      const isFilterVisible = ref(true);
      const filterState = ref({});
      const editOrderMode = ref(false);
      const sortableGroupInstance = ref(null);
      const sortableItemInstances = ref({});

      // --- Status für Sortierung und Auswahl ---
      const sortColumn = ref(null);
      const sortDirection = ref("asc");
      const selectedKontakte = ref(new Set());

      const isAddModalOpen = ref(false);
      const isImportModalOpen = ref(false);

      const newContactData = ref({});
      const addModalVorlageId = ref(activeVorlageId.value);
      const verknuepfungsOptionen = ref({});

      const importStep = ref(1);
      const importTargetVorlageId = ref(null);
      const importFile = ref(null);
      const importData = ref({});
      const importMappings = ref({});
      const importError = ref("");

      // --- Computed Properties ---
      const activeVorlage = computed(() => {
        if (!activeVorlageId.value) return null;
        return vorlagen.value.find((v) => v.id === activeVorlageId.value);
      });

      const sortedKontakte = computed(() => {
        if (!activeVorlage.value) {
          return [];
        }
        if (!sortColumn.value) {
          return activeVorlage.value.kontakte;
        }

        const kontakteCopy = [...activeVorlage.value.kontakte];

        kontakteCopy.sort((a, b) => {
          const valA = a.daten[sortColumn.value] || "";
          const valB = b.daten[sortColumn.value] || "";

          let comparison = 0;

          // Versuch, als Datum zu parsen (Format YYYY-MM-DD oder DD.MM.YYYY)
          const dateA = new Date(
            valA.replace(/(\d{2})\.(\d{2})\.(\d{4})/, "$3-$2-$1")
          );
          const dateB = new Date(
            valB.replace(/(\d{2})\.(\d{2})\.(\d{4})/, "$3-$2-$1")
          );

          if (!isNaN(dateA) && !isNaN(dateB) && valA && valB) {
            comparison = dateA - dateB;
          } else {
            // Versuch, als Zahl zu parsen
            const numA = parseFloat(valA);
            const numB = parseFloat(valB);
            if (!isNaN(numA) && !isNaN(numB)) {
              comparison = numA - numB;
            } else {
              // Standard-String-Vergleich
              comparison = valA.toString().localeCompare(valB.toString());
            }
          }

          return sortDirection.value === "asc" ? comparison : -comparison;
        });

        return kontakteCopy;
      });

      const isAllSelected = computed(() => {
        if (!activeVorlage.value || activeVorlage.value.kontakte.length === 0) {
          return false;
        }
        return (
          selectedKontakte.value.size === activeVorlage.value.kontakte.length
        );
      });

      const addModalVorlage = computed(() =>
        vorlagen.value.find((v) => v.id === addModalVorlageId.value)
      );

      // KORREKTUR: Eigene Computed Property für die Eigenschaften im Modal
      const addModalEigenschaften = computed(() => {
        if (!addModalVorlage.value) return [];
        return addModalVorlage.value.gruppen.flatMap((g) => g.eigenschaften);
      });

      const filteredEigenschaften = computed(() => {
        if (!activeVorlage.value) return [];
        return activeVorlage.value.gruppen
          .flatMap((g) => g.eigenschaften)
          .filter((e) => filterState.value[e.name]);
      });
      const importTargetVorlage = computed(() => {
        if (!importTargetVorlageId.value) return null;
        return vorlagen.value.find((v) => v.id === importTargetVorlageId.value);
      });
      const usedTemplateProperties = computed(() => {
        return new Set(Object.values(importMappings.value).filter(Boolean));
      });

      // --- Watchers ---
      watch(activeVorlageId, () => {
        selectedKontakte.value.clear(); // Auswahl zurücksetzen bei Vorlagenwechsel
      });

      watch(
        activeVorlage,
        async (newVorlage) => {
          if (newVorlage) {
            const newFilterState = {};
            newVorlage.gruppen
              .flatMap((g) => g.eigenschaften)
              .forEach((e) => {
                newFilterState[e.name] = true;
              });
            filterState.value = newFilterState;

            // Lade Verknüpfungsoptionen für die neue Vorlage
            verknuepfungsOptionen.value = {};
            const optionPromises = [];
            for (const gruppe of newVorlage.gruppen) {
              for (const eigenschaft of gruppe.eigenschaften) {
                if (
                  eigenschaft.datentyp === "Verknüpfung" &&
                  eigenschaft.optionen.startsWith("vorlage_id:")
                ) {
                  const linkedVorlageId = eigenschaft.optionen.split(":")[1];
                  const promise = fetch(
                    `/api/kontakte-by-vorlage/${linkedVorlageId}`
                  )
                    .then((response) => (response.ok ? response.json() : []))
                    .then((data) => {
                      verknuepfungsOptionen.value[eigenschaft.id] = data;
                    })
                    .catch((error) => {
                      console.error(
                        "Fehler beim Laden der Verknüpfungs-Optionen:",
                        error
                      );
                      verknuepfungsOptionen.value[eigenschaft.id] = [];
                    });
                  optionPromises.push(promise);
                }
              }
            }
            await Promise.all(optionPromises);
          }
        },
        { immediate: true }
      );

      // --- Methoden ---
      const getVerknuepfungDisplayName = (eigenschaft, kontaktId) => {
        if (
          !eigenschaft ||
          !kontaktId ||
          !verknuepfungsOptionen.value[eigenschaft.id]
        ) {
          return `ID: ${kontaktId}`;
        }
        const options = verknuepfungsOptionen.value[eigenschaft.id];
        const found = options.find((opt) => opt.id == kontaktId); // Use == for loose comparison
        return found ? found.display_name : `ID: ${kontaktId} (ungültig)`;
      };

      const sortBy = (columnName) => {
        if (sortColumn.value === columnName) {
          sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
        } else {
          sortColumn.value = columnName;
          sortDirection.value = "asc";
        }
      };

      const toggleSelection = (kontaktId) => {
        if (selectedKontakte.value.has(kontaktId)) {
          selectedKontakte.value.delete(kontaktId);
        } else {
          selectedKontakte.value.add(kontaktId);
        }
      };

      const toggleSelectAll = () => {
        if (isAllSelected.value) {
          selectedKontakte.value.clear();
        } else {
          activeVorlage.value.kontakte.forEach((k) =>
            selectedKontakte.value.add(k.id)
          );
        }
      };

      const bulkDelete = async () => {
        const idsToDelete = Array.from(selectedKontakte.value);
        if (idsToDelete.length === 0) {
          alert("Keine Kontakte ausgewählt.");
          return;
        }

        if (
          confirm(
            `Möchtest du wirklich ${idsToDelete.length} Kontakte endgültig löschen?`
          )
        ) {
          try {
            const response = await fetch("/api/kontakte/bulk-delete", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ ids: idsToDelete }),
            });
            const result = await response.json();
            if (result.success) {
              activeVorlage.value.kontakte =
                activeVorlage.value.kontakte.filter(
                  (k) => !selectedKontakte.value.has(k.id)
                );
              selectedKontakte.value.clear();
            } else {
              throw new Error(result.error);
            }
          } catch (error) {
            alert(`Fehler beim Löschen: ${error.message}`);
          }
        }
      };

      const onGroupSort = (event) => {
        const movedItem = activeVorlage.value.gruppen.splice(
          event.oldIndex,
          1
        )[0];
        activeVorlage.value.gruppen.splice(event.newIndex, 0, movedItem);
      };
      const onItemSort = (gruppe, event) => {
        const movedItem = gruppe.eigenschaften.splice(event.oldIndex, 1)[0];
        gruppe.eigenschaften.splice(event.newIndex, 0, movedItem);
      };

      const toggleEditOrderMode = async () => {
        editOrderMode.value = !editOrderMode.value;
        await nextTick();
        if (editOrderMode.value) {
          const groupEl = document.querySelector(".filter-body");
          sortableGroupInstance.value = new Sortable(groupEl, {
            animation: 150,
            onEnd: onGroupSort,
            handle: ".drag-handle",
          });
          activeVorlage.value.gruppen.forEach((gruppe) => {
            const itemEl = document.getElementById(`filter-group-${gruppe.id}`);
            if (itemEl) {
              sortableItemInstances.value[gruppe.id] = new Sortable(itemEl, {
                animation: 150,
                onEnd: (evt) => onItemSort(gruppe, evt),
                handle: ".drag-handle",
              });
            }
          });
        } else {
          if (sortableGroupInstance.value)
            sortableGroupInstance.value.destroy();
          Object.values(sortableItemInstances.value).forEach((instance) =>
            instance.destroy()
          );
          sortableItemInstances.value = {};
        }
      };

      const toggleGroupFilter = (gruppe) => {
        const isAnyActive = gruppe.eigenschaften.some(
          (e) => filterState.value[e.name]
        );
        const newStatus = !isAnyActive;
        gruppe.eigenschaften.forEach((e) => {
          filterState.value[e.name] = newStatus;
        });
      };

      const getGroupToggleState = (gruppe) => {
        if (!gruppe || !gruppe.eigenschaften) return "none";
        const activeCount = gruppe.eigenschaften.filter(
          (e) => filterState.value[e.name]
        ).length;
        if (activeCount === 0) return "none";
        if (activeCount === gruppe.eigenschaften.length) return "all";
        return "some";
      };

      const getToggleIcon = (gruppe) => {
        const state = getGroupToggleState(gruppe);
        if (state === "all") return "/static/img/icon_checkbox_checked.svg";
        if (state === "some") return "/static/img/icon_checkbox_some.svg";
        return "/static/img/icon_checkbox_unchecked.svg";
      };

      const openAddModal = () => (isAddModalOpen.value = true);
      const closeAddModal = () => (isAddModalOpen.value = false);

      const updateField = async (kontakt, fieldName, newValue) => {
        if (kontakt.daten[fieldName] === newValue) return;
        try {
          const response = await fetch(`/api/kontakt/${kontakt.id}/update`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ field: fieldName, value: newValue }),
          });
          if (!response.ok) throw new Error("Update fehlgeschlagen");
          const result = await response.json();
          if (result.success) {
            const originalKontakt = activeVorlage.value.kontakte.find(
              (k) => k.id === kontakt.id
            );
            if (originalKontakt) {
              originalKontakt.daten[fieldName] = newValue;
            }
          }
        } catch (error) {
          console.error("Fehler:", error);
          alert("Speichern fehlgeschlagen.");
        }
      };

      const saveNewContact = async () => {
        if (!addModalVorlageId.value) {
          alert("Bitte eine Vorlage auswählen.");
          return;
        }
        try {
          const response = await fetch("/api/kontakt/neu", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              vorlage_id: addModalVorlageId.value,
              daten: newContactData.value,
            }),
          });
          const result = await response.json();
          if (result.success) {
            const targetVorlage = vorlagen.value.find(
              (v) => v.id === addModalVorlageId.value
            );
            if (targetVorlage) {
              targetVorlage.kontakte.push(result.kontakt);
            }
            closeAddModal();
          } else {
            throw new Error(result.error);
          }
        } catch (error) {
          console.error("Fehler:", error);
          alert("Speichern fehlgeschlagen.");
        }
      };

      const openImportModal = () => {
        importStep.value = 1;
        importData.value = {};
        importMappings.value = {};
        importFile.value = null;
        importError.value = "";
        importTargetVorlageId.value = activeVorlageId.value;
        isImportModalOpen.value = true;
      };

      const closeImportModal = () => (isImportModalOpen.value = false);

      const handleFileUpload = async (event) => {
        const files = event.target.files;
        if (!files || files.length === 0 || !importTargetVorlageId.value) {
          importError.value =
            "Bitte zuerst eine Vorlage auswählen und dann eine oder mehrere Dateien hochladen.";
          return;
        }
        importError.value = "";
        const formData = new FormData();
        for (const file of files) {
          formData.append("files", file);
        }

        try {
          const response = await fetch("/import/upload", {
            method: "POST",
            body: formData,
          });
          const result = await response.json();
          if (!response.ok) {
            throw new Error(result.error || "Unbekannter Fehler");
          }
          importData.value = result;

          const allEigenschaften = importTargetVorlage.value.gruppen.flatMap(
            (g) => g.eigenschaften
          );
          result.headers.forEach((h) => {
            const matchingProp = allEigenschaften.find(
              (p) => p.name.toLowerCase() === h.toLowerCase()
            );
            if (matchingProp) {
              importMappings.value[h] = matchingProp.name;
            } else {
              importMappings.value[h] = "";
            }
          });

          importStep.value = 2;
        } catch (error) {
          importError.value = `Fehler: ${error.message}`;
        }
      };

      const finalizeImport = async () => {
        try {
          const response = await fetch("/import/finalize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              vorlage_id: importTargetVorlageId.value,
              mappings: importMappings.value,
              original_data: importData.value.original_data,
            }),
          });
          const result = await response.json();
          if (result.success) {
            window.location.href = result.redirect_url;
          } else {
            throw new Error(result.error);
          }
        } catch (error) {
          importError.value = `Import fehlgeschlagen: ${error.message}`;
        }
      };

      const getExportUrl = (format) => {
        if (!activeVorlageId.value) return "#";
        return `/export/${activeVorlageId.value}/${format}`;
      };

      return {
        vorlagen,
        activeVorlageId,
        activeVorlage,
        isFilterVisible,
        filterState,
        editOrderMode,
        isAddModalOpen,
        newContactData,
        addModalVorlageId,
        addModalVorlage,
        addModalEigenschaften, // <-- Hier zurückgeben
        verknuepfungsOptionen,
        filteredEigenschaften,
        isImportModalOpen,
        importStep,
        importTargetVorlageId,
        importTargetVorlage,
        importData,
        importMappings,
        importError,
        usedTemplateProperties,
        sortColumn,
        sortDirection,
        sortedKontakte,
        selectedKontakte,
        isAllSelected,
        sortBy,
        toggleSelection,
        toggleSelectAll,
        bulkDelete,
        openAddModal,
        closeAddModal,
        toggleEditOrderMode,
        toggleGroupFilter,
        getGroupToggleState,
        getToggleIcon,
        updateField,
        saveNewContact,
        openImportModal,
        closeImportModal,
        handleFileUpload,
        finalizeImport,
        getExportUrl,
        getVerknuepfungDisplayName,
      };
    },
  });

  app.config.compilerOptions.delimiters = ["{[", "]}"];
  app.mount(appRoot);
});
