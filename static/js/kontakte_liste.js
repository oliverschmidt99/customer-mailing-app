document.addEventListener("DOMContentLoaded", () => {
  const appRoot = document.getElementById("kontakte-app");
  if (!appRoot) return;

  const { createApp, ref, computed, watch, nextTick, onBeforeUnmount } = Vue;

  const app = createApp({
    setup() {
      // --- State ---
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
      const sortColumn = ref(null);
      const sortDirection = ref("asc");
      const selectedKontakte = ref(new Set());
      const isAddModalOpen = ref(false);
      const isImportModalOpen = ref(false);
      const isMultiSelectModalOpen = ref(false);
      const newContactData = ref({});
      const addModalVorlageId = ref(activeVorlageId.value);
      const verknuepfungsOptionen = ref({});
      const multiSelectEditData = ref({
        eigenschaft: null,
        kontakt: null,
        selectedValues: [],
      });
      const importStep = ref(1);
      const importTargetVorlageId = ref(null);
      const importData = ref({});
      const importMappings = ref({});
      const importError = ref("");
      const isUploading = ref(false);
      const uploadProgress = ref(0);
      const uploadStatus = ref("");
      const mappingSearchQuery = ref("");
      const mappingStep = ref(0);
      const tomSelectInstances = {};
      const tomSelectRefs = ref({});

      // --- Computed Properties ---
      const activeVorlage = computed(() => {
        if (!activeVorlageId.value) return null;
        return vorlagen.value.find((v) => v.id === activeVorlageId.value);
      });

      const importTargetVorlage = computed(() => {
        if (!importTargetVorlageId.value) return null;
        return vorlagen.value.find((v) => v.id === importTargetVorlageId.value);
      });

      const allTemplateProperties = computed(() => {
        if (!importTargetVorlage.value) return [];
        return importTargetVorlage.value.gruppen.flatMap(
          (g) => g.eigenschaften
        );
      });

      const filteredTemplateProperties = computed(() => {
        if (!mappingSearchQuery.value) {
          return allTemplateProperties.value;
        }
        const query = mappingSearchQuery.value.toLowerCase();
        return allTemplateProperties.value.filter((prop) =>
          prop.name.toLowerCase().includes(query)
        );
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

          const dateA = new Date(
            valA.replace(/(\d{2})\.(\d{2})\.(\d{4})/, "$3-$2-$1")
          );
          const dateB = new Date(
            valB.replace(/(\d{2})\.(\d{2})\.(\d{4})/, "$3-$2-$1")
          );

          if (!isNaN(dateA) && !isNaN(dateB) && valA && valB) {
            comparison = dateA - dateB;
          } else {
            const numA = parseFloat(valA);
            const numB = parseFloat(valB);
            if (!isNaN(numA) && !isNaN(numB)) {
              comparison = numA - numB;
            } else {
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

      const usedTemplateProperties = computed(() => {
        return new Set(Object.values(importMappings.value).filter(Boolean));
      });

      const totalMappingSteps = computed(() =>
        importTargetVorlage.value
          ? importTargetVorlage.value.gruppen.length + 1
          : 1
      );

      const currentMappingGroup = computed(() => {
        if (
          !importTargetVorlage.value ||
          mappingStep.value >= importTargetVorlage.value.gruppen.length
        ) {
          return null;
        }
        return importTargetVorlage.value.gruppen[mappingStep.value];
      });

      const isFinalMappingStep = computed(() =>
        importTargetVorlage.value
          ? mappingStep.value === importTargetVorlage.value.gruppen.length
          : false
      );

      // --- Watchers ---
      watch(activeVorlageId, () => {
        selectedKontakte.value.clear();
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
          }
        },
        {
          immediate: true,
        }
      );

      watch(importStep, async (newStep) => {
        if (newStep === 2) {
          tomSelectRefs.value = {};
          await nextTick();
          initTomSelects();
        }
      });

      watch([currentMappingGroup, isFinalMappingStep], async () => {
        tomSelectRefs.value = {};
        await nextTick();
        initTomSelects();
      });

      watch(
        importMappings,
        (newMappings) => {
          for (const propName in newMappings) {
            if (
              tomSelectInstances[propName] &&
              tomSelectInstances[propName].getValue() !== newMappings[propName]
            ) {
              tomSelectInstances[propName].setValue(
                newMappings[propName],
                true
              );
            }
          }
        },
        {
          deep: true,
        }
      );

      watch(
        addModalVorlage,
        (newVorlage) => {
          if (newVorlage) {
            newVorlage.gruppen.forEach((g) => {
              g.eigenschaften.forEach((e) => {
                if (e.datentyp === "Auswahl" && e.allow_multiselect) {
                  if (!newContactData.value[e.name]) {
                    newContactData.value[e.name] = [];
                  }
                }
              });
            });
          }
        },
        {
          immediate: true,
          deep: true,
        }
      );

      // --- Methoden ---
      const handleVornameChange = async (event) => {
        const vorname = event.target.value;
        if (vorname && !newContactData.value["Anrede"]) {
          try {
            const response = await fetch(`/api/get-anrede/${vorname}`);
            const data = await response.json();
            if (data.anrede) {
              newContactData.value["Anrede"] = data.anrede;
            }
          } catch (error) {
            console.error("Fehler beim Abrufen der Anrede:", error);
          }
        }
      };

      const initTomSelects = () => {
        for (const key in tomSelectInstances) {
          if (tomSelectInstances[key]) {
            tomSelectInstances[key].destroy();
            delete tomSelectInstances[key];
          }
        }

        for (const propName in tomSelectRefs.value) {
          const el = tomSelectRefs.value[propName];
          if (el && !tomSelectInstances[propName]) {
            tomSelectInstances[propName] = new TomSelect(el, {
              create: false,
              dropdownParent: "body",
            });

            tomSelectInstances[propName].on("change", (value) => {
              importMappings.value[propName] = value;
            });
          }
        }
      };

      const pollStatus = (taskId) => {
        const interval = setInterval(async () => {
          try {
            const response = await fetch(`/import/status/${taskId}`);
            const result = await response.json();

            if (result.status === "processing") {
              const percent = Math.round(
                (result.progress / result.total) * 100
              );
              uploadProgress.value = percent;
              uploadStatus.value = `Verarbeite Datei ${result.progress} von ${result.total}... ${percent}%`;
            } else if (result.status === "complete") {
              clearInterval(interval);
              isUploading.value = false;
              importData.value = result.data;

              const newMappings = {};
              allTemplateProperties.value.forEach((prop) => {
                const matchingHeader = (result.data.headers || []).find(
                  (h) => h.toLowerCase() === prop.name.toLowerCase()
                );
                newMappings[prop.name] = matchingHeader || "";
              });
              importMappings.value = newMappings;

              importStep.value = 2;
            }
          } catch (error) {
            clearInterval(interval);
            isUploading.value = false;
            importError.value =
              "Fehler bei der Abfrage des Verarbeitungsstatus.";
          }
        }, 1000);
      };

      const finalizeImport = async () => {
        const mappingsForBackend = {};
        for (const templateProp in importMappings.value) {
          const fileHeader = importMappings.value[templateProp];
          if (fileHeader) {
            mappingsForBackend[fileHeader] = templateProp;
          }
        }

        try {
          const response = await fetch("/import/finalize", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              vorlage_id: importTargetVorlageId.value,
              mappings: mappingsForBackend,
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

        if (editOrderMode.value) {
          await nextTick();
          const groupEl = document.querySelector(".filter-body");
          if (groupEl) {
            sortableGroupInstance.value = new Sortable(groupEl, {
              animation: 150,
              onEnd: onGroupSort,
              handle: ".drag-handle",
            });
          }
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
          sortableGroupInstance.value = null;
          sortableItemInstances.value = {};
        }
      };

      const getVerknuepfungDisplayName = (eigenschaft, kontaktId) => {
        if (
          !eigenschaft ||
          !kontaktId ||
          !verknuepfungsOptionen.value[eigenschaft.id]
        ) {
          return `ID: ${kontaktId}`;
        }
        const options = verknuepfungsOptionen.value[eigenschaft.id];
        const found = options.find((opt) => opt.id == kontaktId);
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
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                ids: idsToDelete,
              }),
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
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              field: fieldName,
              value: newValue,
            }),
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
            headers: {
              "Content-Type": "application/json",
            },
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
        mappingStep.value = 0;
        mappingSearchQuery.value = "";
        importData.value = {};
        importMappings.value = {};
        importError.value = "";
        importTargetVorlageId.value = activeVorlageId.value;
        isImportModalOpen.value = true;
      };

      const closeImportModal = () => (isImportModalOpen.value = false);

      const nextMappingStep = () => {
        if (mappingStep.value < totalMappingSteps.value - 1) {
          mappingStep.value++;
        }
      };

      const prevMappingStep = () => {
        if (mappingStep.value > 0) {
          mappingStep.value--;
        } else {
          importStep.value = 1;
        }
      };

      const handleFileUpload = (event) => {
        const files = event.target.files;
        if (!files || files.length === 0 || !importTargetVorlageId.value) {
          importError.value =
            "Bitte zuerst eine Vorlage auswählen und dann eine oder mehrere Dateien hochladen.";
          return;
        }

        importError.value = "";
        isUploading.value = true;
        uploadProgress.value = 0;
        uploadStatus.value = `Lade ${files.length} Datei(en) hoch...`;

        const formData = new FormData();
        for (const file of files) {
          formData.append("files", file);
        }

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/import/upload", true);

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            uploadProgress.value = percentComplete;
            uploadStatus.value = `Lade hoch... ${percentComplete}%`;
          }
        };

        xhr.onload = () => {
          if (xhr.status === 202) {
            const result = JSON.parse(xhr.responseText);
            if (result.task_id) {
              uploadStatus.value =
                "Upload abgeschlossen. Starte Verarbeitung...";
              pollStatus(result.task_id);
            }
          } else {
            try {
              const result = JSON.parse(xhr.responseText);
              importError.value = `Fehler: ${result.error || xhr.statusText}`;
            } catch (e) {
              importError.value = `Ein Serverfehler ist aufgetreten (Status: ${xhr.status}).`;
            }
            isUploading.value = false;
          }
        };

        xhr.onerror = () => {
          isUploading.value = false;
          importError.value = "Ein Netzwerkfehler ist aufgetreten.";
        };

        xhr.send(formData);
      };

      const getExportUrl = (format) => {
        if (!activeVorlageId.value) return "#";
        return `/export/${activeVorlageId.value}/${format}`;
      };

      const openMultiSelectModal = (eigenschaft, kontakt) => {
        const currentValues = kontakt.daten[eigenschaft.name] || "";
        multiSelectEditData.value = {
          eigenschaft: eigenschaft,
          kontakt: kontakt,
          selectedValues: currentValues
            ? currentValues.split(",").map((v) => v.trim())
            : [],
        };
        isMultiSelectModalOpen.value = true;
      };

      const saveMultiSelect = () => {
        const { kontakt, eigenschaft, selectedValues } =
          multiSelectEditData.value;
        const newValue = selectedValues.join(", ");
        updateField(kontakt, eigenschaft.name, newValue);
        isMultiSelectModalOpen.value = false;
      };

      onBeforeUnmount(() => {
        for (const key in tomSelectInstances) {
          if (tomSelectInstances[key]) tomSelectInstances[key].destroy();
        }
      });

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
        addModalEigenschaften,
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
        isUploading,
        uploadProgress,
        uploadStatus,
        isMultiSelectModalOpen,
        multiSelectEditData,
        openMultiSelectModal,
        saveMultiSelect,
        mappingSearchQuery,
        filteredTemplateProperties,
        mappingStep,
        totalMappingSteps,
        currentMappingGroup,
        isFinalMappingStep,
        nextMappingStep,
        prevMappingStep,
        tomSelectRefs,
        handleVornameChange,
      };
    },
  });

  app.config.compilerOptions.delimiters = ["{[", "]}"];
  app.mount(appRoot);
});
