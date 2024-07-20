const cyrb53 = (str, seed = 0) => {
  let h1 = 0xdeadbeef ^ seed,
    h2 = 0x41c6ce57 ^ seed;
  for (let i = 0, ch; i < str.length; i++) {
    ch = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
  h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
  h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);

  return 4294967296 * (2097151 & h2) + (h1 >>> 0);
};

const output = {};
let hook = null;
let outputString;

function extract() {
  if (!hook) {
    const temp = document.getElementsByClassName("suspended-feed");
    if (temp.length) hook = temp[0].parentElement.parentElement.parentElement;
  }

  if (hook) {
    const targets = Array.from(hook.childNodes).filter(
      (v) => v.classList.length
    );

    for (const target of targets) {
      try {
        const mesgs = [];
        const imgs = [];
        let extra = 0;

        for (const mesg of target.querySelectorAll(
          'div[data-ad-comet-preview="message"] span[dir="auto"] > div > div'
        ))
          mesgs.push(mesg.textContent);

        const imgsElem = target.querySelector(
          'div[data-ad-comet-preview="message"]'
        );
        if (imgsElem) {
          for (const img of imgsElem.parentElement.parentElement.lastChild.getElementsByTagName(
            "img"
          ))
            imgs.push(img.src);

          const match = imgsElem.textContent.match(/\+(\d+)/);
          if (match) extra = Number(match[1]) - 1;

          const data = { message: mesgs, images: imgs, extra: extra };
          const hash = cyrb53(JSON.stringify(data));

          if (!output[hash]) output[hash] = data;
        }
      } catch (e) {
        console.log(e);
      }
    }
  }

  outputString = JSON.stringify(Object.values(output));
}

document.addEventListener("scroll", extract);
