/* static/cotton/widgets/image_preview_file.js */

function initImagePreviewFile(componentEl, previewDisplayEl) {
    const inputEl = componentEl.querySelector("input[type=file]");
    const formEl = inputEl.closest("form");
  
    inputEl.addEventListener("change", function () {
      previewImages();
    });
  
    formEl?.addEventListener("reset", function () {
      if (previewDisplayEl) previewDisplayEl.innerHTML = "";
    });
  
    function previewImages() {
      if (!previewDisplayEl) {
        console.warn("previewDisplayEl is not defined");
        return;
      }
  
      previewDisplayEl.innerHTML = "";
      if (!inputEl.files) {
        console.warn("[previewImages] input is", inputEl);
      } else {
        const filesArray = Array.from(inputEl.files);
  
        filesArray.forEach((currentFile) => {
          const reader = new FileReader();
          reader.onload = function (e) {
            const imageDataUrl = e.target.result;
            const container = document.createElement("div");
            container.className = "relative";
  
            const img = document.createElement("img");
            img.src = imageDataUrl;
            img.className = "w-[75px] h-[75px] object-cover rounded-lg";
            container.appendChild(img);
  
            /*
            removeButton.type = "button"을 명시하지 않으면, text enter 입력 시에 removeButton이 클릭되는 현상.
  
            1. HTML 폼 내부에 있는 버튼은 기본적으로 type="submit"으로 취급됩니다. <= 크로스 브라우징 이슈 있음.
            2. 폼 내의 input 필드에서 Enter 키를 누르면, 브라우저는 submit 타입의 버튼을 찾아 클릭 이벤트를 발생시킵니다. <= 🔥
            3. type="button"으로 지정된 버튼은 폼 제출과 무관한 일반 버튼으로 취급됩니다.
            4. removeButton에 type="button"을 추가함으로써, 이 버튼이 폼 제출과 관련없는 일반 버튼임을 명시했습니다.
             */
  
            const removeButton = document.createElement("button");
            removeButton.innerHTML = "X";
            removeButton.type = "button";
            removeButton.className =
              "absolute top-0 right-0 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center cursor-pointer";
            removeButton.onclick = function () {
              container.remove();
  
              const data_transfer = new DataTransfer();
  
              Array.from(inputEl.files)
                .filter((file) => file.name !== currentFile.name)
                .forEach((file) => {
                  data_transfer.items.add(file);
                });
  
              inputEl.files = data_transfer.files;
            };
            container.appendChild(removeButton);
  
            previewDisplayEl.appendChild(container);
          };
          reader.readAsDataURL(currentFile);
        });
      }
    }
  }