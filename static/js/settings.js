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

  // --- Vue App für Einstellungen ---
  const settingsAppRoot = document.getElementById("settings-app");
  if (settingsAppRoot) {
    const { createApp, ref, computed, watch } = Vue;

    createApp({
      setup() {
        // --- Daten für Auswahloptionen ---
        const initialOptionsData = JSON.parse(
          document.getElementById("selection-options-data").textContent
        );
        const options = ref(JSON.parse(JSON.stringify(initialOptionsData)));
        const saveStatus = ref("");
        const isSuccess = ref(false);

        // --- Daten für Absenderadresse ---
        const initialConfigData = JSON.parse(
          document.getElementById("config-data").textContent
        );
        const senderAddress = ref(initialConfigData.sender_address || "");
        const addressSaveStatus = ref("");
        const isAddressSuccess = ref(false);

        // --- Computed Properties ---
        const hasChanges = computed(() => {
          return (
            JSON.stringify(options.value) !== JSON.stringify(initialOptionsData)
          );
        });
        const hasAddressChanges = computed(() => {
          return senderAddress.value !== initialConfigData.sender_address;
        });

        // --- Methoden für Auswahloptionen ---
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
              Object.assign(
                initialOptionsData,
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

        // --- Methoden für Absenderadresse ---
        const saveSenderAddress = async () => {
          addressSaveStatus.value = "Speichert...";
          isAddressSuccess.value = false;
          try {
            const response = await fetch("/settings/api/config", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ sender_address: senderAddress.value }),
            });
            const result = await response.json();
            if (result.success) {
              addressSaveStatus.value = result.message;
              isAddressSuccess.value = true;
              initialConfigData.sender_address = senderAddress.value;
            } else {
              throw new Error(result.error);
            }
          } catch (error) {
            addressSaveStatus.value = `Fehler: ${error.message}`;
            isAddressSuccess.value = false;
          }
        };

        // --- Watchers ---
        watch(saveStatus, (newValue) => {
          if (newValue) {
            setTimeout(() => {
              saveStatus.value = "";
            }, 3000);
          }
        });
        watch(addressSaveStatus, (newValue) => {
          if (newValue) {
            setTimeout(() => {
              addressSaveStatus.value = "";
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
          senderAddress,
          addressSaveStatus,
          isAddressSuccess,
          hasAddressChanges,
          saveSenderAddress,
        };
      },
      delimiters: ["{[", "]}"],
    }).mount(settingsAppRoot);
  }
});
