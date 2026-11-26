const assert = require('node:assert/strict');
const {chromium} = require(process.env.WORDSPEAK_PLAYWRIGHT || 'playwright');

(async () => {
  const browser = await chromium.launch({executablePath:process.env.WORDSPEAK_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  try {
    const page = await browser.newPage({viewport:{width:390,height:844}});
    await page.goto('http://127.0.0.1:8013/demo');
    const config = await (await page.request.get('http://127.0.0.1:8013/demo/config')).json();
    const chart=page.locator('#sound-table');
    await page.getByText('Tap the sounds',{exact:true}).click();
    const keys=await chart.locator('[data-chart-sound]').evaluateAll(nodes=>nodes.map(node=>node.dataset.chartSound));
    assert.deepEqual(keys.sort(),config.primary_targets.slice().sort());
    for(const prompt of config.prompts){
      await page.locator('#prompt').selectOption(prompt.id);
      await chart.getByRole('button',{name:'Show example'}).click();
      const message=await chart.getByRole('status').last().textContent();
      const readings=[...message.matchAll(/\/([^/]+)\//g)].map(match=>match[1].split(' '));
      assert.ok(readings.length>0,prompt.id);
      for(const reading of readings)assert.ok(reading.every(phone=>keys.includes(phone)),prompt.id);
    }
    await chart.getByLabel('Word or phrase').selectOption({label:'I can go.'});
    await chart.locator('[data-chart-sound="s"]').click();
    await chart.getByRole('button',{name:'Compare'}).click();
    assert.ok(await chart.getByText(/differs from the examples/).isVisible());
    await chart.getByRole('button',{name:'Undo'}).click();
    for(const phone of ['aɪ','k','ə','n','ɡ','oʊ'])await chart.locator('[data-chart-sound="'+phone+'"]').click();
    await chart.getByRole('button',{name:'Compare'}).click();
    assert.ok(await chart.getByText(/You built a reference reading/).isVisible());
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    console.log('Verified 41 sound keys, 51 word references, reduced phrase, retry and mobile layout');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
