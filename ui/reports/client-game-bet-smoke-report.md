# 客户端游戏投注冒烟报告

- 扫描时间: 2026-08-26T09:14:11.565Z
- 游戏: Lucky Penny (lucky_penny)
- 游戏页: `/s-game-page/17453858840928`
- 执行真实点击: true
- 点击前等待: 25000ms
- 点击后等待: 8000ms
- 点击位置: {"x":1264,"y":430}
- Frame 数: 4
- 点击后新增疑似游戏请求数: 3
- 点击前截图: `/Users/rayleigh/qa-automation/ui/results/screenshots/lucky_penny-before-spin.png`
- 点击后截图: `/Users/rayleigh/qa-automation/ui/results/screenshots/lucky_penny-after-spin.png`

## Frame

- `https://client-fat.filbet2025.com/s-game-page/17453858840928`
- `https://gate.stage1.bng.games/op/filbetcom-stage/game.html?<redacted>`
- `https://static-stage.neurorestorativeals.xyz/gm/index.html?<redacted>`
- `https://static-stage.neurorestorativeals.xyz/aux/games/aux_b/runner/index.html?<redacted>`

## 关键接口

| Method | HTTP | URL |
|---|---:|---|
| POST | 200 | `/member/game/rank` |
| GET | 200 | `/finance/wallet` |
| GET | 200 | `/game/launch?code=<redacted>` |
| POST | 200 | `/process/` |

## 结论

- 已点击游戏内 Spin/Bet 区域，并捕获到点击后的第三方游戏请求。最终账变以钱包余额或投注记录接口为准。
