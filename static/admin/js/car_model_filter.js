document.addEventListener("DOMContentLoaded", function () {
    var carBrandField = document.querySelector("#id_car_brand");
    var carModelField = document.querySelector("#id_car_model");

    function updateCarModels() {
        var brandId = carBrandField.value;
        if (!brandId) {
            carModelField.innerHTML = '<option value="">---------</option>';
            return;
        }

        fetch(`/admin/get-car-models/?brand_id=${brandId}`)
            .then(response => response.json())
            .then(data => {
                carModelField.innerHTML = '<option value="">---------</option>';
                data.models.forEach(function (model) {
                    var option = document.createElement("option");
                    option.value = model.id;
                    option.textContent = model.name;
                    carModelField.appendChild(option);
                });
            })
            .catch(error => console.error("Error fetching car models:", error));
    }

    if (carBrandField) {
        carBrandField.addEventListener("change", updateCarModels);
        updateCarModels();  // Sahifa yuklanganda ham ishlaydi
    }
});
