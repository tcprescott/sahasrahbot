#!/usr/bin/env node

const vm = require("node:vm");
const fs = require("node:fs");
const crypto = require("node:crypto");

//-----------------------------------------------------------------
// CLI usage information.
//-----------------------------------------------------------------

const printUsage = () => {
   console.log("node dash.cli.js -r <vanillaRom> -p <preset>");
};

//-----------------------------------------------------------------
// Process command line arguments.
//-----------------------------------------------------------------

if (process.argv.length != 6) {
   printUsage();
   return 1;
}

let vanillaPath = "";
let preset = "";

for (let i = 2; i < process.argv.length; i++) {
   if (process.argv[i] == "-r") {
      vanillaPath = process.argv[++i];
   } else if (process.argv[i] == "-p") {
      preset = process.argv[++i];
   } else {
      console.log("INVALID OPTION: ", process.argv[i]);
      printUsage();
      return 1;
   }
}

//-----------------------------------------------------------------
// Make sure the vanilla ROM path is correct.
//-----------------------------------------------------------------

if (!fs.existsSync(vanillaPath)) {
   console.log("Could not find ROM:", vanillaPath);
   return 1;
}

//-----------------------------------------------------------------
// Read the vanilla ROM and establish the base URL.
//-----------------------------------------------------------------

const baseUrl = "https://dashrando.github.io/";
let userRom = fs.readFileSync(vanillaPath);
let vanillaRom = null;
const vanillaHash =
   "12b77c4bc9c1832cee8881244659065ee1d84c70c3d29e6eaf92e6798cc2ca72";
const headeredHash =
   "9a4441809ac9331cdbc6a50fba1a8fbfd08bc490bc8644587ee84a4d6f924fea"

//-----------------------------------------------------------------
// Verify the vanilla ROM checksum.
//-----------------------------------------------------------------
const verifyAndSetRom = (rom) => {
   let hash = crypto.createHash("sha256");
   hash.update(rom);
   const signature = hash.digest("hex");
   if (signature === vanillaHash) {
      return rom
   } else if (signature === headeredHash) {
      console.warn('You have entered a headered ROM. The header will now be removed.')
      const unheaderedContent = rom.slice(512)
      return verifyAndSetRom(unheaderedContent)
   }
   throw Error('Invalid vanilla ROM')
}

try {
   vanillaRom = verifyAndSetRom(userRom);
} catch (e) {
   console.log("Invalid vanilla ROM:", vanillaPath);
   return 1;
}

//-----------------------------------------------------------------
// Generate a seed from the specified preset.
//-----------------------------------------------------------------

fetch(baseUrl + "app/dash.min.js")
   .then((res) => res.text())
   .then((text) => {
      const script = new vm.Script(text);
      script.runInThisContext();

      const [basePatchUrl, seedPatch, fileName] = generateFromPreset(preset);

      if (!basePatchUrl || !seedPatch || !fileName) {
         console.log("Failed to generate preset:", preset);
         return 1;
      }

      fetch(baseUrl + basePatchUrl)
         .then((res) => res.arrayBuffer())
         .then((buffer) => {
            const rom = patchRom(
               vanillaRom,
               new BpsPatch(new Uint8Array(buffer)),
               seedPatch
            );
            fs.writeFileSync(fileName, rom);
            console.log("Generated: " + fileName);
         });
   });