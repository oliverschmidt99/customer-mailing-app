// static/js/kontakt_editor.js
document.addEventListener("DOMContentLoaded", () => {
  const { createApp, ref, onMounted } = Vue;

  createApp({
    setup() {
      const vorlage = JSON.parse(
        document.getElementById("vorlage-for-json-data").textContent
      );
      const kontaktDaten = JSON.parse(
        document.getElementById("kontakt-daten-for-json-data").textContent
      );

      const formData = ref({ ...kontaktDaten });
      const verknuepfungsOptionen = ref({});

      onMounted(async () => {
        for (const gruppe of vorlage.gruppen) {
          for (const eigenschaft of gruppe.eigenschaften) {
            if (
              eigenschaft.datentyp === "Verknüpfung" &&
              eigenschaft.optionen.startsWith("vorlage_id:")
            ) {
              const vorlageId = eigenschaft.optionen.split(":")[1];
              try {
                const response = await fetch(
                  `/api/kontakte-by-vorlage/${vorlageId}`
                );
                verknuepfungsOptionen.value[eigenschaft.id] =
                  await response.json();
              } catch (error) {
                console.error(error);
              }
            }
          }
        }
      });

      return { vorlage, formData, verknuepfungsOptionen };
    },
  }).mount("#kontakt-editor-app");
});
