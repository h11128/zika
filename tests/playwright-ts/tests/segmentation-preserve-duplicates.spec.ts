import { test, expect } from '@playwright/test';
import { ZikaAppPage } from '../page-objects/ZikaAppPage';

// E2E: 勾选“保留重复词”后点击“智能分词”，应保留重复词
// 覆盖 rerun 时序 + 复选框状态快照的真实浏览器行为

test.describe('Segmentation - Preserve Duplicates', () => {
  let zikaApp: ZikaAppPage;

  test.beforeEach(async ({ page }) => {
    zikaApp = new ZikaAppPage(page);
    await zikaApp.goto();
  });

  test('保留重复词 + 智能分词 应保留重复', async ({ page }) => {
    // 进入手动输入模式
    await page.getByText('手动输入', { exact: true }).click();

    const textarea = page.getByLabel('输入汉字（空格分隔）');
    const input = '你好 你 叫 什么 名字 我 的 是 心美 李大文 你好 你 叫 什么 名字 我 的 是 心美 李大文';
    await textarea.fill(input);

    // 勾选“保留重复词” - 某些主题下原生input不可见，点击标签更稳
    const preserveLabel = page.getByText('保留重复词', { exact: true });
    await preserveLabel.scrollIntoViewIfNeeded().catch(() => {});
    await preserveLabel.click();

    // 点击“智能分词”
    await page.getByRole('button', { name: '🔄 智能分词' }).click();

    // 断言：分词后文本仍应包含重复的“你好 … 你好”（事件驱动、无固定timeout）
    await expect(textarea).toHaveValue(/你好.*你好/);
  });
});

