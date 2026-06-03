from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from studio_shell.page_shell import page_shell
from studio_shell.shell_ui import format_extra_context, inject_style

st.set_page_config(page_title="射擊遊戲", page_icon="🎯", layout="wide")
inject_style()


GAME_HTML = """
<div class="game-wrap">
  <canvas id="game" width="760" height="520" tabindex="0"></canvas>
  <div class="hud">
    <button id="startBtn">開始</button>
    <button id="pauseBtn">暫停</button>
    <button id="resetBtn">重來</button>
    <span id="score">Score 0</span>
    <span id="lives">Lives 3</span>
  </div>
</div>

<style>
  .game-wrap {
    width: 100%;
    max-width: 800px;
    margin: 0 auto;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  #game {
    width: 100%;
    aspect-ratio: 76 / 52;
    display: block;
    border: 1px solid rgba(255,255,255,.18);
    border-radius: 8px;
    background: #202725;
    outline: none;
    touch-action: none;
  }
  .hud {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 10px;
    flex-wrap: wrap;
  }
  .hud button {
    border: 1px solid rgba(255,255,255,.22);
    border-radius: 6px;
    background: #1d2733;
    color: #fff;
    padding: 8px 14px;
    cursor: pointer;
  }
  .hud button:hover { background: #263444; }
  .hud span {
    min-width: 92px;
    color: #e8edf3;
    font-weight: 700;
  }
</style>

<script>
(() => {
  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");
  const scoreEl = document.getElementById("score");
  const livesEl = document.getElementById("lives");
  const startBtn = document.getElementById("startBtn");
  const pauseBtn = document.getElementById("pauseBtn");
  const resetBtn = document.getElementById("resetBtn");

  const keys = new Set();
  let running = false;
  let gameOver = false;
  let score = 0;
  let lives = 3;
  let lastTime = 0;
  let spawnTimer = 0;
  let shotCooldown = 0;
  let wave = 1;

  const mouse = { x: 420, y: 260, down: false };
  const player = { x: 120, y: 410, r: 15, speed: 210, angle: 0 };
  const bullets = [];
  const enemies = [];
  const sparks = [];
  const walls = [
    { x: 0, y: 0, w: 760, h: 24 },
    { x: 0, y: 496, w: 760, h: 24 },
    { x: 0, y: 0, w: 24, h: 520 },
    { x: 736, y: 0, w: 24, h: 520 },
    { x: 120, y: 90, w: 180, h: 28 },
    { x: 420, y: 72, w: 34, h: 160 },
    { x: 540, y: 166, w: 140, h: 30 },
    { x: 78, y: 245, w: 150, h: 34 },
    { x: 308, y: 292, w: 205, h: 28 },
    { x: 590, y: 326, w: 32, h: 118 },
  ];
  const spawnPoints = [
    { x: 650, y: 82 },
    { x: 665, y: 435 },
    { x: 94, y: 88 },
    { x: 382, y: 430 },
  ];

  function reset() {
    running = false;
    gameOver = false;
    score = 0;
    lives = 3;
    lastTime = 0;
    spawnTimer = 0;
    shotCooldown = 0;
    wave = 1;
    player.x = 120;
    player.y = 410;
    player.angle = 0;
    bullets.length = 0;
    enemies.length = 0;
    sparks.length = 0;
    updateHud();
    draw(0);
    canvas.focus();
  }

  function updateHud() {
    scoreEl.textContent = `Score ${score}`;
    livesEl.textContent = `Lives ${lives}`;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function circleRectHit(cx, cy, r, rect) {
    const nearestX = clamp(cx, rect.x, rect.x + rect.w);
    const nearestY = clamp(cy, rect.y, rect.y + rect.h);
    return Math.hypot(cx - nearestX, cy - nearestY) < r;
  }

  function hitsWall(x, y, r) {
    return walls.some((wall) => circleRectHit(x, y, r, wall));
  }

  function moveActor(actor, dx, dy, dt) {
    const nx = actor.x + dx * actor.speed * dt;
    if (!hitsWall(nx, actor.y, actor.r)) actor.x = nx;
    const ny = actor.y + dy * actor.speed * dt;
    if (!hitsWall(actor.x, ny, actor.r)) actor.y = ny;
  }

  function shoot() {
    if (shotCooldown > 0 || gameOver) return;
    const speed = 560;
    bullets.push({
      x: player.x + Math.cos(player.angle) * 18,
      y: player.y + Math.sin(player.angle) * 18,
      vx: Math.cos(player.angle) * speed,
      vy: Math.sin(player.angle) * speed,
      r: 4,
    });
    shotCooldown = 0.22;
  }

  function spawnEnemy() {
    const point = spawnPoints[Math.floor(Math.random() * spawnPoints.length)];
    enemies.push({
      x: point.x,
      y: point.y,
      r: 14,
      speed: 72 + Math.random() * 28 + wave * 4,
      angle: 0,
    });
  }

  function burst(x, y) {
    for (let i = 0; i < 10; i += 1) {
      sparks.push({
        x,
        y,
        vx: -80 + Math.random() * 160,
        vy: -80 + Math.random() * 160,
        life: 0.38,
      });
    }
  }

  function step(dt) {
    if (!running || gameOver) return;

    let dx = (keys.has("ArrowRight") || keys.has("KeyD") ? 1 : 0) -
      (keys.has("ArrowLeft") || keys.has("KeyA") ? 1 : 0);
    let dy = (keys.has("ArrowDown") || keys.has("KeyS") ? 1 : 0) -
      (keys.has("ArrowUp") || keys.has("KeyW") ? 1 : 0);
    const length = Math.hypot(dx, dy);
    if (length > 0) {
      dx /= length;
      dy /= length;
    }

    player.angle = Math.atan2(mouse.y - player.y, mouse.x - player.x);
    moveActor(player, dx, dy, dt);

    if (keys.has("Space") || mouse.down) shoot();
    shotCooldown = Math.max(0, shotCooldown - dt);

    spawnTimer -= dt;
    if (spawnTimer <= 0) {
      spawnEnemy();
      wave = 1 + Math.floor(score / 100);
      spawnTimer = Math.max(0.55, 1.45 - wave * 0.08);
    }

    for (const bullet of bullets) {
      bullet.x += bullet.vx * dt;
      bullet.y += bullet.vy * dt;
    }
    for (const enemy of enemies) {
      const angle = Math.atan2(player.y - enemy.y, player.x - enemy.x);
      enemy.angle = angle;
      moveActor(enemy, Math.cos(angle), Math.sin(angle), dt);
    }
    for (const spark of sparks) {
      spark.x += spark.vx * dt;
      spark.y += spark.vy * dt;
      spark.life -= dt;
    }

    for (let i = enemies.length - 1; i >= 0; i -= 1) {
      const enemy = enemies[i];
      let removed = false;
      for (let j = bullets.length - 1; j >= 0; j -= 1) {
        const bullet = bullets[j];
        const dist = Math.hypot(enemy.x - bullet.x, enemy.y - bullet.y);
        if (dist < enemy.r + bullet.r) {
          bullets.splice(j, 1);
          enemies.splice(i, 1);
          score += 10;
          burst(enemy.x, enemy.y);
          updateHud();
          removed = true;
          break;
        }
      }
      if (removed) continue;

      if (Math.hypot(enemy.x - player.x, enemy.y - player.y) < enemy.r + player.r) {
        enemies.splice(i, 1);
        lives -= 1;
        burst(player.x, player.y);
        updateHud();
      }
    }

    for (let i = bullets.length - 1; i >= 0; i -= 1) {
      const bullet = bullets[i];
      const out = bullet.x < -20 || bullet.x > canvas.width + 20 ||
        bullet.y < -20 || bullet.y > canvas.height + 20;
      if (out || hitsWall(bullet.x, bullet.y, bullet.r)) {
        bullets.splice(i, 1);
      }
    }
    for (let i = sparks.length - 1; i >= 0; i -= 1) {
      if (sparks[i].life <= 0) sparks.splice(i, 1);
    }

    if (lives <= 0) {
      lives = 0;
      running = false;
      gameOver = true;
      updateHud();
    }
  }

  function drawGrid() {
    ctx.strokeStyle = "rgba(255,255,255,.045)";
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#26312e";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawGrid();

    ctx.fillStyle = "#1b211f";
    for (const wall of walls) {
      ctx.fillRect(wall.x, wall.y, wall.w, wall.h);
      ctx.strokeStyle = "rgba(255,255,255,.11)";
      ctx.strokeRect(wall.x + 0.5, wall.y + 0.5, wall.w - 1, wall.h - 1);
    }

    ctx.fillStyle = "rgba(80, 109, 91, .42)";
    ctx.fillRect(40, 42, 150, 26);
    ctx.fillRect(470, 394, 120, 24);

    drawPerson(player, {
      shirt: "#3fbf7f",
      pants: "#243949",
      skin: "#f1c7a5",
      vest: "#244d3a",
      weapon: "#1d2329",
    });

    ctx.fillStyle = "#f8d66d";
    for (const bullet of bullets) {
      ctx.beginPath();
      ctx.arc(bullet.x, bullet.y, bullet.r, 0, Math.PI * 2);
      ctx.fill();
    }

    for (const enemy of enemies) {
      drawPerson(enemy, {
        shirt: "#b94b5f",
        pants: "#352932",
        skin: "#e8b79b",
        vest: "#612935",
        weapon: "#2a2024",
      });
    }

    for (const spark of sparks) {
      ctx.globalAlpha = Math.max(0, spark.life / 0.38);
      ctx.fillStyle = "#fbbf24";
      ctx.fillRect(spark.x, spark.y, 3, 3);
      ctx.globalAlpha = 1;
    }

    ctx.strokeStyle = "rgba(255,255,255,.75)";
    ctx.beginPath();
    ctx.arc(mouse.x, mouse.y, 10, 0, Math.PI * 2);
    ctx.moveTo(mouse.x - 15, mouse.y);
    ctx.lineTo(mouse.x + 15, mouse.y);
    ctx.moveTo(mouse.x, mouse.y - 15);
    ctx.lineTo(mouse.x, mouse.y + 15);
    ctx.stroke();

    ctx.fillStyle = "rgba(232,237,243,.9)";
    ctx.font = "16px system-ui";
    ctx.fillText("WASD / 方向鍵移動，滑鼠瞄準，點擊或空白鍵射擊", 34, 50);

    if (!running && !gameOver) {
      ctx.fillStyle = "rgba(0,0,0,.42)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#fff";
      ctx.font = "700 30px system-ui";
      ctx.fillText("按開始進入遊戲", canvas.width / 2 - 115, canvas.height / 2);
    }
    if (gameOver) {
      ctx.fillStyle = "rgba(0,0,0,.55)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#fff";
      ctx.font = "700 34px system-ui";
      ctx.fillText("Game Over", canvas.width / 2 - 92, canvas.height / 2 - 10);
      ctx.font = "18px system-ui";
      ctx.fillText(`你的分數：${score}`, canvas.width / 2 - 48, canvas.height / 2 + 24);
    }
  }

  function roundedRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  function drawPerson(actor, colors) {
    ctx.save();
    ctx.translate(actor.x, actor.y);
    ctx.rotate(actor.angle);

    ctx.fillStyle = "rgba(0,0,0,.24)";
    ctx.beginPath();
    ctx.ellipse(-1, 8, 18, 11, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = colors.pants;
    roundedRect(-8, 8, 6, 15, 3);
    ctx.fill();
    roundedRect(2, 8, 6, 15, 3);
    ctx.fill();

    ctx.fillStyle = colors.shirt;
    roundedRect(-10, -9, 20, 22, 7);
    ctx.fill();

    ctx.fillStyle = colors.vest;
    roundedRect(-6, -6, 12, 17, 4);
    ctx.fill();

    ctx.fillStyle = colors.skin;
    roundedRect(-17, -4, 7, 17, 4);
    ctx.fill();
    roundedRect(10, -4, 7, 17, 4);
    ctx.fill();

    ctx.fillStyle = colors.skin;
    ctx.beginPath();
    ctx.arc(0, -18, 8, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "rgba(44, 35, 28, .75)";
    ctx.beginPath();
    ctx.arc(-2, -21, 6, Math.PI, Math.PI * 1.95);
    ctx.fill();

    ctx.fillStyle = colors.weapon;
    roundedRect(6, -5, 25, 6, 3);
    ctx.fill();
    roundedRect(17, 0, 6, 10, 2);
    ctx.fill();

    ctx.fillStyle = "rgba(255,255,255,.72)";
    ctx.beginPath();
    ctx.arc(4, -19, 1.6, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function loop(time) {
    if (!lastTime) lastTime = time;
    const dt = Math.min(0.033, (time - lastTime) / 1000);
    lastTime = time;
    step(dt);
    draw();
    requestAnimationFrame(loop);
  }

  function isControlKey(code) {
    return [
      "ArrowUp",
      "ArrowDown",
      "ArrowLeft",
      "ArrowRight",
      "KeyW",
      "KeyA",
      "KeyS",
      "KeyD",
      "Space",
    ].includes(code);
  }

  function rememberKey(event, pressed) {
    if (!isControlKey(event.code)) return;
    event.preventDefault();
    event.stopPropagation();
    if (pressed) {
      keys.add(event.code);
    } else {
      keys.delete(event.code);
    }
  }

  canvas.addEventListener("pointerdown", () => canvas.focus());
  canvas.addEventListener("pointermove", (event) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = (event.clientX - rect.left) * (canvas.width / rect.width);
    mouse.y = (event.clientY - rect.top) * (canvas.height / rect.height);
  });
  canvas.addEventListener("mousedown", () => {
    mouse.down = true;
    canvas.focus();
  });
  window.addEventListener("mouseup", () => {
    mouse.down = false;
  });
  document.addEventListener("visibilitychange", () => keys.clear());
  window.addEventListener("blur", () => keys.clear());

  window.addEventListener("keydown", (event) => {
    if (event.repeat && event.code === "Space") {
      event.preventDefault();
      return;
    }
    rememberKey(event, true);
  }, { capture: true });
  window.addEventListener("keyup", (event) => rememberKey(event, false), { capture: true });

  startBtn.addEventListener("click", () => {
    if (gameOver) reset();
    running = true;
    lastTime = 0;
    canvas.focus();
  });
  pauseBtn.addEventListener("click", () => {
    running = false;
    canvas.focus();
  });
  resetBtn.addEventListener("click", reset);

  reset();
  requestAnimationFrame(loop);
})();
</script>
"""


def render_main() -> str:
    st.markdown("#### 地圖射擊練習")
    components.html(GAME_HTML, height=620)

    extra = format_extra_context(
        "射擊遊戲",
        遊戲類型="俯視角 2D 地圖射擊遊戲",
        操作方式="WASD 或方向鍵移動，滑鼠瞄準，點擊或空白鍵射擊",
        目前功能="地圖牆壁、玩家人物、敵人人物、準星、子彈、分數、生命值、碰撞判定",
        練習方向="可以請 Agent 加入不同地圖、掩體、補包、武器切換或關卡目標",
    )

    st.markdown("#### 給 Agent 的摘要")
    st.code(extra, language="text")

    st.markdown("#### 右欄可以這樣問")
    st.markdown(
        """
- 「幫我加一種會斜著移動的敵人。」
- 「幫我加入生命值補包，每 15 秒出現一次。」
- 「幫我新增第二張地圖，並加上更多掩體。」
"""
    )
    return extra


page_shell(
    "射擊遊戲",
    "用 Canvas 做一個有地圖、人物與掩體的俯視角射擊小遊戲。",
    render_main,
    page_name="射擊遊戲",
)
