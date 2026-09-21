// Move a freshly built stylesheet into static/ in one step.
//
// Tailwind writes its output straight to the destination, which takes a moment
// for a file this size. A browser asking for the stylesheet during that moment
// gets half of it - the colours and the buttons, none of the layout - and may
// hold on to that copy. Building to a temporary file and renaming it means the
// destination is always a complete stylesheet: a rename is atomic, so a request
// sees either the old file or the new one.
const fs = require('fs');
const path = require('path');

const [from, to] = process.argv.slice(2);
if (!from || !to) {
  console.error('usage: node publish.js <built file> <destination>');
  process.exit(1);
}

const source = path.resolve(__dirname, from);
const destination = path.resolve(__dirname, to);
fs.mkdirSync(path.dirname(destination), { recursive: true });
fs.renameSync(source, destination);
console.log(`${path.basename(destination)}  ${(fs.statSync(destination).size / 1024).toFixed(1)} KB`);
