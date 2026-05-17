/**
 * Generate PDF from Buildathon submission markdown.
 * Usage: node scripts/generate-submission-pdf.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const mdPath = path.join(ROOT, 'docs', 'CURSOR-BUILDATHON-SUBMISSION.md');
const pdfPath = path.join(ROOT, 'docs', 'CURSOR-BUILDATHON-SUBMISSION.pdf');
const md = fs.readFileSync(mdPath, 'utf8');

// Simple MD → HTML (headings, tables, lists, bold, hr)
function mdToHtml(src) {
  const lines = src.split('\n');
  let html = '';
  let inTable = false;
  let inList = false;

  const flushList = () => {
    if (inList) {
      html += '</ul>\n';
      inList = false;
    }
  };
  const flushTable = () => {
    if (inTable) {
      html += '</tbody></table>\n';
      inTable = false;
    }
  };

  const inline = (s) =>
    s
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>');

  for (const line of lines) {
    if (line.startsWith('# ')) {
      flushList();
      flushTable();
      html += `<h1>${inline(line.slice(2))}</h1>\n`;
    } else if (line.startsWith('## ')) {
      flushList();
      flushTable();
      html += `<h2>${inline(line.slice(3))}</h2>\n`;
    } else if (line.startsWith('### ')) {
      flushList();
      flushTable();
      html += `<h3>${inline(line.slice(4))}</h3>\n`;
    } else if (line.startsWith('---')) {
      flushList();
      flushTable();
      html += '<hr/>\n';
    } else if (line.startsWith('|')) {
      flushList();
      const cells = line.split('|').slice(1, -1).map((c) => c.trim());
      if (cells.every((c) => /^[-:]+$/.test(c))) continue;
      if (!inTable) {
        html += '<table><thead><tr>';
        cells.forEach((c) => {
          html += `<th>${inline(c)}</th>`;
        });
        html += '</tr></thead><tbody>\n';
        inTable = true;
      } else {
        html += '<tr>';
        cells.forEach((c) => {
          html += `<td>${inline(c)}</td>`;
        });
        html += '</tr>\n';
      }
    } else if (line.startsWith('- ')) {
      flushTable();
      if (!inList) {
        html += '<ul>\n';
        inList = true;
      }
      html += `<li>${inline(line.slice(2))}</li>\n`;
    } else if (line.startsWith('```')) {
      flushList();
      flushTable();
      /* skip code fence markers — pre blocks handled simply */
    } else if (line.trim() === '') {
      flushList();
      flushTable();
      html += '<br/>\n';
    } else if (line.startsWith('    ') || line.startsWith('```')) {
      flushList();
      flushTable();
      html += `<pre class="code">${line.replace(/</g, '&lt;')}</pre>\n`;
    } else {
      flushList();
      flushTable();
      html += `<p>${inline(line)}</p>\n`;
    }
  }
  flushList();
  flushTable();
  return html;
}

const htmlDoc = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Aivura — Cursor Buildathon Submission</title>
<style>
  @page { size: A4; margin: 18mm 16mm; }
  body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1a1a1a; max-width: 100%; }
  h1 { font-size: 20pt; color: #4c1d95; border-bottom: 2px solid #7c3aed; padding-bottom: 6px; margin-top: 0; page-break-after: avoid; }
  h2 { font-size: 14pt; color: #5b21b6; margin-top: 22px; page-break-after: avoid; }
  h3 { font-size: 11.5pt; color: #6d28d9; page-break-after: avoid; }
  table { width: 100%; border-collapse: collapse; margin: 10px 0 14px; font-size: 9.5pt; page-break-inside: avoid; }
  th, td { border: 1px solid #d4d4d8; padding: 6px 8px; text-align: left; vertical-align: top; }
  th { background: #f4f4f5; font-weight: 600; }
  ul { margin: 6px 0 12px 18px; }
  li { margin-bottom: 4px; }
  pre.code { background: #f4f4f5; padding: 8px; font-size: 8pt; overflow-x: auto; white-space: pre-wrap; border-radius: 4px; }
  code { background: #f4f4f5; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
  hr { border: none; border-top: 1px solid #e4e4e7; margin: 16px 0; }
  p { margin: 6px 0; }
  .cover { text-align: center; padding: 40px 0 30px; page-break-after: always; }
  .cover h1 { border: none; font-size: 26pt; }
  .cover p { color: #52525b; font-size: 11pt; }
  strong { color: #18181b; }
  a { color: #7c3aed; }
</style>
</head>
<body>
<div class="cover">
  <h1>Aivura</h1>
  <p><strong>CURSOR BUILDATHON · PROJECT SUBMISSION DOCUMENT</strong></p>
  <p>Cursor × TechTalk360 · Best use of n8n</p>
  <p>Repository: github.com/Kiruthiyan/n8n_aivura · Bot: @Aivura_bot</p>
  <p style="margin-top:24px;font-size:9pt;color:#71717a;">Confidential — For Authorized Use Only</p>
</div>
${mdToHtml(md.replace(/^# CURSOR BUILDATHON[\s\S]*?^---\n/m, ''))}
</body>
</html>`;

const htmlPath = path.join(ROOT, 'docs', 'CURSOR-BUILDATHON-SUBMISSION.html');
fs.writeFileSync(htmlPath, htmlDoc.replace(/<\/motion\.motion.div>/g, '</motion.div>').replace(/<motion\.div>/g, '<div>'));

async function tryMdToPdf() {
  try {
    const { mdToPdf } = await import('md-to-pdf');
    await mdToPdf({ path: mdPath }, { dest: pdfPath, pdf_options: { format: 'A4', margin: '18mm 16mm', printBackground: true } });
    return true;
  } catch {
    return false;
  }
}

async function tryPuppeteer() {
  try {
    const puppeteer = await import('puppeteer');
    const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
    const page = await browser.newPage();
    await page.goto(`file:///${htmlPath.replace(/\\/g, '/')}`, { waitUntil: 'networkidle0' });
    await page.pdf({
      path: pdfPath,
      format: 'A4',
      margin: { top: '18mm', right: '16mm', bottom: '18mm', left: '16mm' },
      printBackground: true,
    });
    await browser.close();
    return true;
  } catch (e) {
    console.error('Puppeteer failed:', e.message);
    return false;
  }
}

console.log('Generating submission PDF…\n');

if (await tryMdToPdf()) {
  console.log('✓ PDF:', pdfPath);
} else if (await tryPuppeteer()) {
  console.log('✓ PDF (via HTML):', pdfPath);
} else {
  console.log('✓ HTML (open in browser → Print → Save as PDF):', htmlPath);
  console.log('\nInstall optional: npm install md-to-pdf puppeteer');
}
