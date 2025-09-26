document.addEventListener("DOMContentLoaded", () => {
  const editorRoot = document.getElementById("vorlage-editor-app");
  if (!editorRoot) {
    return;
  }

  const {
    createApp,
    ref,
    onMounted,
    computed,
    watch,
    nextTick,
    onBeforeUnmount,
  } = Vue;

  const app = createApp({
    setup() {
      // Daten aus dem HTML auslesen
      const initialVorlageData = JSON.parse(
        document.getElementById("vorlage-data").textContent
      );
      const actionUrl = ref(
        document.getElementById("action-url-data").textContent.slice(1, -1)
      );
      // NEU: Lade die globalen Auswahloptionen
      const selectionOptions = ref(
        JSON.parse(
          document.getElementById("selection-options-data").textContent
        )
      );

      // Reaktive Zustände
      const vorlage = ref(JSON.parse(JSON.stringify(initialVorlageData))); // Tiefe Kopie als Arbeitskopie
      const isSaveAsModalOpen = ref(false);
      const newVorlageName = ref("");
      const suggestions = ref({ categories: [] });
      const selectedSuggestionCategory = ref(null);
      const viewMode = ref("list");
      const activeModal = ref(null);
      const editedGroup = ref(null);
      const editedGroupIndex = ref(null);
      const groupSortable = ref(null);
      const propertySortables = ref({});
      const collapsedGroups = ref({});
      const allVorlagen = ref(
        JSON.parse(document.getElementById("all-vorlagen-data").textContent)
      );

      // --- Computed Properties ---
      const pageTitle = computed(() => {
        if (initialVorlageData.is_standard) {
          return `Standard-Vorlage: ${initialVorlageData.name}`;
        }
        return initialVorlageData.id
          ? `Vorlage bearbeiten: ${initialVorlageData.name}`
          : "Neue Vorlage erstellen";
      });

      const hasChanges = computed(() => {
        return (
          JSON.stringify(vorlage.value) !== JSON.stringify(initialVorlageData)
        );
      });

      // --- Methoden ---

      const applyGlobalOption = (event, propertyIndex) => {
        const selectedOptionName = event.target.value;
        if (selectedOptionName && selectionOptions.value[selectedOptionName]) {
          const values = selectionOptions.value[selectedOptionName];
          editedGroup.value.eigenschaften[propertyIndex].optionen =
            values.join(", ");
        }
      };

      const handleSave = () => {
        if (initialVorlageData.is_standard && hasChanges.value) {
          newVorlageName.value = initialVorlageData.name + " (Kopie)";
          isSaveAsModalOpen.value = true;
          return;
        }

        if (!initialVorlageData.is_standard) {
          saveVorlage();
          return;
        }

        alert("Keine Änderungen zum Speichern vorhanden.");
      };

      // ... Rest der JS-Datei bleibt unverändert ...
      // (saveVorlage, saveAsNewVorlage, toggleGroupCollapse, etc.)

      const saveVorlage = async () => {
        try {
          const r = await fetch(actionUrl.value, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(vorlage.value),
          });
          if (!r.ok) throw new Error("Speichern fehlgeschlagen");
          const res = await r.json();
          if (res.redirect_url) window.location.href = res.redirect_url;
        } catch (e) {
          alert("Speichern fehlgeschlagen.");
        }
      };

      const saveAsNewVorlage = async () => {
        const payload = JSON.parse(JSON.stringify(vorlage.value));
        delete payload.id;
        payload.name = newVorlageName.value;
        payload.is_standard = false;

        try {
          const r = await fetch("/vorlagen/speichern", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!r.ok) {
            const errorData = await r.json();
            throw new Error(
              errorData.error || "Speichern als neue Vorlage fehlgeschlagen"
            );
          }
          const res = await r.json();
          if (res.redirect_url) {
            window.location.href = res.redirect_url;
          }
        } catch (e) {
          alert(e.message);
        }
      };

      const toggleGroupCollapse = (index) => {
        collapsedGroups.value[index] = !collapsedGroups.value[index];
      };

      const expandAll = () => {
        vorlage.value.gruppen.forEach((_, index) => {
          collapsedGroups.value[index] = false;
        });
      };

      const collapseAll = () => {
        vorlage.value.gruppen.forEach((_, index) => {
          collapsedGroups.value[index] = true;
        });
      };

      const initSortables = () => {
        destroySortables();
        const groupContainer = document.getElementById("group-list-container");
        if (groupContainer) {
          groupSortable.value = new Sortable(groupContainer, {
            animation: 150,
            handle: ".drag-handle",
            onEnd: (event) => {
              const movedItem = vorlage.value.gruppen.splice(
                event.oldIndex,
                1
              )[0];
              vorlage.value.gruppen.splice(event.newIndex, 0, movedItem);
            },
          });
        }
        vorlage.value.gruppen.forEach((gruppe, index) => {
          const propContainer = document.querySelector(
            `.property-list-container[data-group-index='${index}']`
          );
          if (propContainer) {
            propertySortables.value[index] = new Sortable(propContainer, {
              animation: 150,
              handle: ".drag-handle",
              onEnd: (event) => {
                const movedItem = gruppe.eigenschaften.splice(
                  event.oldIndex,
                  1
                )[0];
                gruppe.eigenschaften.splice(event.newIndex, 0, movedItem);
              },
            });
          }
        });
      };

      const destroySortables = () => {
        if (groupSortable.value) groupSortable.value.destroy();
        Object.values(propertySortables.value).forEach((s) => s.destroy());
        groupSortable.value = null;
        propertySortables.value = {};
      };

      onMounted(async () => {
        try {
          const suggResponse = await fetch("/api/attribute-suggestions");
          suggestions.value = await suggResponse.json();
        } catch (error) {
          console.error("Fehler:", error);
        }

        if (viewMode.value === "list") {
          await nextTick();
          initSortables();
        }
      });

      watch(viewMode, async (newMode) => {
        if (newMode === "list") {
          await nextTick();
          initSortables();
        } else {
          destroySortables();
        }
      });

      watch(
        () => vorlage.value.gruppen,
        async () => {
          if (viewMode.value === "list") {
            await nextTick();
            initSortables();
          }
        },
        { deep: true }
      );

      onBeforeUnmount(destroySortables);

      const closeModal = () => {
        activeModal.value = null;
        editedGroup.value = null;
        editedGroupIndex.value = null;
      };

      const openGroupEditModal = (index) => {
        editedGroupIndex.value = index;
        editedGroup.value = JSON.parse(
          JSON.stringify(vorlage.value.gruppen[index])
        );
        activeModal.value = "groupEdit";
      };

      const removeGruppe = (index) => {
        const groupName = vorlage.value.gruppen[index].name;
        if (
          confirm(`Möchtest du die Gruppe "${groupName}" wirklich löschen?`)
        ) {
          vorlage.value.gruppen.splice(index, 1);
        }
      };

      const saveGroup = () => {
        if (editedGroupIndex.value !== null) {
          vorlage.value.gruppen[editedGroupIndex.value] = editedGroup.value;
        }
        closeModal();
      };

      const addEigenschaft = () => {
        editedGroup.value.eigenschaften.push({
          name: "",
          datentyp: "Text",
          optionen: "",
        });
      };

      const removeEigenschaft = (index) => {
        editedGroup.value.eigenschaften.splice(index, 1);
      };

      const addGroupFromSuggestion = () => {
        if (!selectedSuggestionCategory.value) return;
        const cat = selectedSuggestionCategory.value;
        const g = {
          name: cat.name,
          eigenschaften: cat.attributes.map((attr) => ({
            name: attr,
            datentyp: "Text",
            optionen: "",
          })),
        };
        vorlage.value.gruppen.push(g);
        selectedSuggestionCategory.value = null;
      };

      const addEmptyGruppe = () => {
        vorlage.value.gruppen.push({ name: "Neue Gruppe", eigenschaften: [] });
      };

      return {
        vorlage,
        suggestions,
        selectionOptions, // <-- NEU
        pageTitle,
        selectedSuggestionCategory,
        viewMode,
        activeModal,
        editedGroup,
        isSaveAsModalOpen,
        newVorlageName,
        addGroupFromSuggestion,
        addEmptyGruppe,
        openGroupEditModal,
        saveGroup,
        addEigenschaft,
        removeEigenschaft,
        closeModal,
        handleSave,
        saveAsNewVorlage,
        allVorlagen,
        collapsedGroups,
        toggleGroupCollapse,
        removeGruppe,
        expandAll,
        collapseAll,
        applyGlobalOption, // <-- NEU
      };
    },
  });
  app.config.compilerOptions.delimiters = ["{[", "]}"];
  app.mount(editorRoot);
});
