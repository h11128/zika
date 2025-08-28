import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

// TDD: 验证点击“智能分词”后，“保留重复词”的勾选不会丢失

test.describe('Segmentation - Checkbox Persistence', () => {
  let zikaApp: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    zikaApp = new ZikaAppPage(page);
    await zikaApp.goto();
  });

  test('点击智能分词后 勾选状态应保持（等待预览稳定+3秒）', async ({ page }) => {
    // 进入手动输入模式
    await page.getByText('手动输入', { exact: true }).click();

    const textarea = page.getByLabel('输入汉字（空格分隔）');
    await textarea.fill('你好 你 叫 什么 名字 我 的 是 心美 李大文 你好 你 叫 什么 名字 我 的 是 心美 李大文');

    // 勾选“保留重复词”，用标签文本更稳
    const preserveLabel = page.getByText('保留重复词', { exact: true });
    await preserveLabel.scrollIntoViewIfNeeded().catch(() => {});
    await preserveLabel.click();

    // 验证已勾选
    const checkbox = page.getByRole('checkbox', { name: '保留重复词' });
    await expect(checkbox).toBeChecked();

    // 点击“智能分词”
    await page.getByRole('button', { name: '🔄 智能分词' }).click();

    // 等预览稳定：页码组合框出现（预览渲染完毕的可靠信号）
    await page.getByRole('combobox', { name: '页码' }).waitFor({ state: 'visible' });

    // 额外等待 3 秒
    await page.waitForTimeout(3000);

    // 断言：勾选仍保持
    await expect(checkbox).toBeChecked();
  });
});

