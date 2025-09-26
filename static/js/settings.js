// static/js/settings.js
document.addEventListener("DOMContentLoaded", () => {
  // --- Dark Mode Schalter ---
  const themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    themeToggle.checked =
      document.documentElement.getAttribute("data-theme") === "dark";

    themeToggle.addEventListener("change", () => {
      const newTheme = themeToggle.checked ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("theme", newTheme);
    });
  }

  // --- Vue App für Auswahloptionen ---
  const optionsAppRoot = document.getElementById("selection-options-app");
  if (optionsAppRoot) {
    const { createApp, ref, computed, watch } = Vue;

    createApp({
      setup() {
        const initialData = JSON.parse(
          document.getElementById("selection-options-data").textContent
        );

        const options = ref(JSON.parse(JSON.stringify(initialData)));
        const saveStatus = ref("");
        const isSuccess = ref(false);

        const hasChanges = computed(() => {
          return JSON.stringify(options.value) !== JSON.stringify(initialData);
        });

        const addOption = () => {
          options.value.push({ name: "", values: "" });
        };

        const removeOption = (index) => {
          options.value.splice(index, 1);
        };

        const saveOptions = async () => {
          saveStatus.value = "Speichert...";
          isSuccess.value = false;
          try {
            const response = await fetch("/settings/api/selection-options", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ options: options.value }),
            });
            const result = await response.json();
            if (result.success) {
              saveStatus.value = result.message;
              isSuccess.value = true;
              // Aktualisiere die initialen Daten, um den "hasChanges"-Status zurückzusetzen
              Object.assign(
                initialData,
                JSON.parse(JSON.stringify(options.value))
              );
            } else {
              throw new Error(result.error);
            }
          } catch (error) {
            saveStatus.value = `Fehler: ${error.message}`;
            isSuccess.value = false;
          }
        };

        // Setze die Nachricht nach einiger Zeit zurück
        watch(saveStatus, (newValue) => {
          if (newValue) {
            setTimeout(() => {
              saveStatus.value = "";
            }, 3000);
          }
        });

        return {
          options,
          hasChanges,
          saveStatus,
          isSuccess,
          addOption,
          removeOption,
          saveOptions,
        };
      },
      delimiters: ["{[", "]}"],
    }).mount(optionsAppRoot);
  }
});
