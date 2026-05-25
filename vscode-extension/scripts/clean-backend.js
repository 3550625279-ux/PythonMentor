const fs = require('fs');
const path = require('path');

const dest = path.resolve(__dirname, '..');
const dirs = ['python-backend', 'knowledge-base'];

for (const dir of dirs) {
    const target = path.join(dest, dir);
    if (fs.existsSync(target)) {
        fs.rmSync(target, { recursive: true, force: true });
        console.log(`Removed ${dir}/`);
    }
}
