import puppeteer from 'puppeteer-core';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const FIXTURES_DIR = path.resolve(__dirname, '../../../tests/fixtures');
const SENIOR_PDF = path.join(FIXTURES_DIR, 'sample_resumes/senior_software_engineer.pdf');
const SENIOR_DOCX = path.join(FIXTURES_DIR, 'sample_resumes/senior_software_engineer.docx');
const CORRUPT_PDF = path.join(FIXTURES_DIR, 'sample_resumes/corrupt_file.pdf');
const FULLSTACK_JD_PATH = path.join(FIXTURES_DIR, 'sample_jobs/fullstack_engineer.txt');

const fullstackJD = fs.readFileSync(FULLSTACK_JD_PATH, 'utf-8');

async function runE2E() {
  console.log('================================================================');
  console.log('Starting End-to-End Browser Verification for Resume ATS Website');
  console.log('================================================================');

  if (!fs.existsSync(CHROME_PATH)) {
    throw new Error(`Chrome not found at ${CHROME_PATH}`);
  }

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,900'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });

  const consoleLogs = [];
  const networkErrors = [];

  page.on('console', (msg) => {
    const text = msg.text();
    consoleLogs.push(`[Console ${msg.type()}] ${text}`);
    if (msg.type() === 'error') {
      console.error(`  -> Browser Console Error: ${text}`);
    }
  });

  page.on('requestfailed', (req) => {
    networkErrors.push(`${req.method()} ${req.url()}: ${req.failure()?.errorText}`);
  });

  try {
    // -------------------------------------------------------------------------
    // Step 1: Load Website & Check Health Status
    // -------------------------------------------------------------------------
    console.log('\n[Step 1] Navigating to http://127.0.0.1:5173...');
    await page.goto('http://127.0.0.1:5173', { waitUntil: 'domcontentloaded', timeout: 15000 });

    const title = await page.title();
    console.log(`✓ Page Loaded. Title: "${title}"`);
    if (!title.includes('Resume ATS Score Checker')) {
      throw new Error(`Unexpected page title: ${title}`);
    }

    // Verify API status badge
    await page.waitForSelector('.header-badge', { timeout: 5000 });
    const badgeText = await page.$eval('.header-badge', (el) => el.textContent?.trim());
    console.log(`✓ API Health Badge in UI: "${badgeText}"`);
    if (badgeText !== 'API Online') {
      throw new Error(`Expected "API Online" in header badge, got "${badgeText}"`);
    }

    // -------------------------------------------------------------------------
    // Step 2: Empty Form Submission Validation
    // ----------------------------------------------------------------------
    // ---
    console.log('\n[Step 2] Testing empty form submission validation...');
    const submitBtn = await page.$('button[type="submit"]');
    await submitBtn.click();

    await page.waitForSelector('.alert-danger', { timeout: 3000 });
    const errorAlerts = await page.$$eval('.alert-danger span', (els) => els.map((e) => e.textContent));
    console.log(`✓ Validation alerts caught: ${JSON.stringify(errorAlerts)}`);
    const hasFileError = errorAlerts.some((t) => t.includes('upload your resume'));
    const hasJobError = errorAlerts.some((t) => t.includes('paste the target job description'));
    if (!hasFileError || !hasJobError) {
      throw new Error('Validation errors missing for empty submission');
    }

    // -------------------------------------------------------------------------
    // Step 3: Insufficient Job Description Length Validation
    // -------------------------------------------------------------------------
    console.log('\n[Step 3] Testing short job description validation (< 5 words)...');
    const fileInput = await page.$('#resume-file-input');
    await fileInput.uploadFile(SENIOR_PDF);

    await page.waitForSelector('.selected-file-card', { timeout: 3000 });
    const uploadedName = await page.$eval('.file-name', (el) => el.textContent?.trim());
    console.log(`✓ File selected: "${uploadedName}"`);

    await page.type('#job-description-textarea', 'Python developer');
    await submitBtn.click();

    await page.waitForFunction(
      () => document.body.innerText.includes('at least 5 words required'),
      { timeout: 3000 }
    );
    console.log('✓ Caught short job description validation error');

    // Clear textarea
    await page.$eval('#job-description-textarea', (el) => (el.value = ''));

    // -------------------------------------------------------------------------
    // Step 4: Full End-to-End Analysis with PDF Resume
    // -------------------------------------------------------------------------
    console.log('\n[Step 4] Submitting full analysis with PDF resume and complete job description...');
    await page.type('#job-description-textarea', fullstackJD);

    // Verify word counter updated
    const metaCounter = await page.$eval('.textarea-meta', (el) => el.textContent?.trim());
    console.log(`✓ Textarea meta info: "${metaCounter}"`);

    // Click Analyze Resume
    console.log('  -> Clicking Analyze Resume button...');
    await submitBtn.click();

    // Check loading state appears
    await page.waitForSelector('.loading-box', { timeout: 2000 });
    console.log('✓ Loading state rendered ("Analyzing Your Resume")');

    // Wait for results dashboard to render
    await page.waitForSelector('.results-dashboard', { timeout: 15000 });
    console.log('✓ Results Dashboard successfully rendered!');

    // Inspect rendered score
    const scoreVal = await page.$eval('.score-number', (el) => el.textContent?.trim());
    const scoreMax = await page.$eval('.score-max', (el) => el.textContent?.trim());
    const tierBadge = await page.$eval('.score-tier-badge', (el) => el.textContent?.trim());
    const scoreSummary = await page.$eval('.score-summary-text', (el) => el.textContent?.trim());
    console.log(`✓ Rendered Score: ${scoreVal}${scoreMax} (${tierBadge})`);
    console.log(`✓ Summary: "${scoreSummary}"`);

    // Inspect Categories
    const categories = await page.$$eval('.category-card', (cards) =>
      cards.map((c) => ({
        name: c.querySelector('.category-card-name')?.textContent?.trim(),
        points: c.querySelector('.category-card-points')?.textContent?.trim(),
        explanation: c.querySelector('.category-card-explanation')?.textContent?.trim(),
      }))
    );
    console.log(`✓ Rendered ${categories.length} Evaluation Categories:`);
    categories.forEach((cat) => console.log(`   - ${cat.name}: ${cat.points}`));
    if (categories.length !== 5) {
      throw new Error(`Expected 5 category cards, found ${categories.length}`);
    }

    // Inspect Matched Keywords chips
    const keywordChips = await page.$$eval('.chip-success', (chips) =>
      chips.map((c) => c.textContent?.trim())
    );
    console.log(`✓ Rendered ${keywordChips.length} Keywords & Technologies chips: ${keywordChips.slice(0, 6).join(', ')}...`);

    // Inspect Recommendations
    const recommendations = await page.$$eval('.recommendation-card', (cards) =>
      cards.map((c) => ({
        title: c.querySelector('.rec-title')?.textContent?.trim(),
        priority: c.querySelector('.rec-priority-badge')?.textContent?.trim(),
      }))
    );
    console.log(`✓ Rendered ${recommendations.length} Actionable Recommendations:`);
    recommendations.forEach((r) => console.log(`   - [${r.priority}] ${r.title}`));

    // Inspect Disclaimer
    const disclaimer = await page.$eval('.disclaimer-card', (el) => el.textContent?.trim());
    console.log(`✓ Disclaimer present: "${disclaimer.slice(0, 100)}..."`);

    // -------------------------------------------------------------------------
    // Step 5: Test "Analyze Another Resume" Reset Action
    // -------------------------------------------------------------------------
    console.log('\n[Step 5] Testing "Analyze Another Resume" reset action...');
    const resetBtn = await page.waitForSelector('button[aria-label="Analyze another resume"]', { timeout: 5000 });
    await resetBtn.click();

    // Verify workspace form is back and previous results are cleared
    await page.waitForSelector('.workspace-card', { timeout: 3000 });
    const isDashboardPresent = await page.$('.results-dashboard');
    if (isDashboardPresent) {
      throw new Error('Results dashboard still present after reset');
    }
    console.log('✓ Reset action cleared results and returned to analysis workspace.');

    // -------------------------------------------------------------------------
    // Step 6: Full End-to-End Analysis with DOCX Resume
    // -------------------------------------------------------------------------
    console.log('\n[Step 6] Submitting full analysis with DOCX resume...');
    const fileInput2 = await page.$('#resume-file-input');
    await fileInput2.uploadFile(SENIOR_DOCX);
    await page.waitForSelector('.selected-file-card', { timeout: 3000 });
    const docxName = await page.$eval('.file-name', (el) => el.textContent?.trim());
    console.log(`✓ DOCX file selected: "${docxName}"`);

    await page.type('#job-description-textarea', fullstackJD);

    const submitBtn2 = await page.$('button[type="submit"]');
    await submitBtn2.click();

    await page.waitForSelector('.results-dashboard', { timeout: 15000 });
    const docxScore = await page.$eval('.score-number', (el) => el.textContent?.trim());
    const docxTier = await page.$eval('.score-tier-badge', (el) => el.textContent?.trim());
    console.log(`✓ DOCX Rendered Score: ${docxScore}/100 (${docxTier})`);

    // Reset again
    const resetBtn2 = await page.waitForSelector('button[aria-label="Analyze another resume"]', { timeout: 5000 });
    await resetBtn2.click();
    await page.waitForSelector('.workspace-card', { timeout: 3000 });

    // -------------------------------------------------------------------------
    // Step 7: Test Corrupted File Error Handling
    // -------------------------------------------------------------------------
    console.log('\n[Step 7] Testing Corrupted File error handling from backend...');
    const fileInput3 = await page.$('#resume-file-input');
    await fileInput3.uploadFile(CORRUPT_PDF);
    await page.waitForSelector('.selected-file-card', { timeout: 3000 });

    await page.type('#job-description-textarea', fullstackJD);
    const submitBtn3 = await page.$('button[type="submit"]');
    await submitBtn3.click();

    // Verify error banner is rendered in workspace
    await page.waitForSelector('.alert-danger', { timeout: 5000 });
    const errText = await page.$eval('.alert-danger', (el) => el.textContent?.trim());
    console.log(`✓ Backend error message properly rendered in UI: "${errText}"`);
    if (!errText.includes('EXTRACTION_FAILED') && !errText.includes('corrupted') && !errText.includes('Analysis Error')) {
      throw new Error(`Unexpected error text: ${errText}`);
    }

    console.log('\n================================================================');
    console.log('All Browser End-to-End Verification Steps Succeeded Perfectly!');
    console.log('================================================================');
  } catch (err) {
    console.error('\n❌ E2E Verification Failed with error:', err);
    throw err;
  } finally {
    await browser.close();
  }
}

runE2E().catch((err) => {
  console.error(err);
  process.exit(1);
});
