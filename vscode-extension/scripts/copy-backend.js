const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const dest = path.resolve(__dirname, '..');

const dirs = ['python-backend', 'knowledge-base'];

for (const dir of dirs) {
    const src = path.join(root, dir);
    const dst = path.join(dest, dir);

    if (!fs.existsSync(src)) {
        console.warn(`Warning: ${src} not found, skipping.`);
        continue;
    }

    // Use robocopy on Windows for reliable recursive copy with exclusions
    if (process.platform === 'win32') {
        const { execSync } = require('child_process');
        const exclude = dir === 'python-backend'
            ? '/XD .venv __pycache__ chroma_db data .git /XF .env test_*.py .gitignore'
            : '/XD __pycache__ .git';

        try {
            execSync(`robocopy "${src}" "${dst}" /E /NFL /NDL /NJH /NJS /nc /ns /np ${exclude}`, {
                stdio: 'pipe',
            });
        } catch (e) {
            // robocopy exit codes 0-7 are success
            if (e.status > 7) {
                console.error(`Failed to copy ${dir}: ${e.message}`);
                process.exit(1);
            }
        }
    } else {
        // Unix: rsync with excludes
        const { execSync } = require('child_process');
        const exclude = dir === 'python-backend'
            ? '--exclude=.venv --exclude=__pycache__ --exclude=chroma_db --exclude=data --exclude=.env --exclude="test_*.py" --exclude=.gitignore'
            : '--exclude=__pycache__ --exclude=.git';

        execSync(`rsync -a ${exclude} "${src}/" "${dst}/"`, { stdio: 'inherit' });
    }

    console.log(`Copied ${dir}/`);
}
