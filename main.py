import json
import random
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
import astrbot.api.message_components as Comp
from astrbot.api.star import Context, Star, register
from PIL import Image, ImageDraw, ImageFont


PLUGIN_DIR = Path(__file__).resolve().parent
DATA_DIR = PLUGIN_DIR / "data"
TAROT_DIR = DATA_DIR / "TarotImages"
TAROT_JSON = TAROT_DIR / "ff14_tarot.json"
FONT_PATH = DATA_DIR / "simhei.ttf"


def random_left_right() -> str:
    result = []
    for _ in range(5):
        result.append("右" if random.random() > 0.5 else "左")
    return " ".join(result)


def random_lottery() -> str:
    last_num_list = []
    lottery_list = []
    for _ in range(3):
        while True:
            last_num = random.randint(0, 9)
            if last_num not in last_num_list:
                last_num_list.append(last_num)
                break
        lottery_list.append(
            f"{random.randint(0, 9)} {random.randint(0, 9)} "
            f"{random.randint(0, 9)} {last_num}"
        )
    return "\n".join(lottery_list)


def text_to_image(text: str, output_path: Path, width_now: int = 20) -> None:
    font_size = 20
    font = ImageFont.truetype(str(FONT_PATH), size=font_size)

    cursor = 0
    wrapped = ""
    for char in text:
        if char == "\n":
            if len(wrapped) > 1:
                wrapped += char
            cursor = 0
            continue
        cursor += 2 if len(char.encode()) > 1 else 1
        wrapped += char
        if cursor >= 2 * width_now:
            wrapped += "\n"
            cursor = 0

    lines = wrapped.split("\n")
    image = Image.new(
        "RGB",
        (int(width_now * 22), (len(lines) + 1) * (font_size + 2)),
        (255, 255, 255),
    )
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), wrapped, font=font, fill=(0, 0, 0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="JPEG")


def load_tarot() -> dict:
    with TAROT_JSON.open("r", encoding="utf-8") as tarot_file:
        return json.load(tarot_file)


def choose_tarot(tarot_dict: dict) -> tuple[str, Path]:
    info_now = tarot_dict["_塔罗牌堆"][random.randint(0, 43)]
    text_now = info_now.split("[", 1)[0]
    file_name = info_now.rsplit("/", 1)[-1][:-1].replace(" ", "_")
    return text_now, TAROT_DIR / file_name


def create_help_text() -> str:
    return """【塔塔露现有指令】
()括号表示可选的参数
[选门] 帮你选藏宝洞的门
[仙人彩] 帮你选每周仙人仙彩数字
[抽卡] 随机抽取一张FF14塔罗牌

以下功能仍在迁移中：
[暖暖] [看看微博] [物品] [价格] [房子] [输出] [攻略] [日历] [招募]
"""


@register("astrbot_plugin_tataru", "aaron-li / Codex", "FF14 塔塔露 AstrBot 插件", "0.1.0")
class TataruPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.tarot_dict: dict | None = None
        self.cache_dir = PLUGIN_DIR / ".cache"

    async def initialize(self):
        self.tarot_dict = load_tarot()
        self.cache_dir.mkdir(exist_ok=True)
        logger.info("Tataru AstrBot plugin initialized.")

    @filter.command("帮帮忙")
    async def help(self, event: AstrMessageEvent):
        """显示塔塔露当前已迁移的指令。"""
        yield event.plain_result(create_help_text())

    @filter.command("选门")
    async def precious(self, event: AstrMessageEvent):
        """帮你选藏宝洞的门。"""
        yield event.plain_result("塔塔露在藏宝洞中横冲直撞！\n" + random_left_right())

    @filter.command("仙人彩")
    async def lottery(self, event: AstrMessageEvent):
        """帮你选每周仙人仙彩数字。"""
        yield event.plain_result("塔塔露觉得这个可以！\n" + random_lottery())

    @filter.command("抽卡")
    async def tarot(self, event: AstrMessageEvent):
        """随机抽取一张FF14塔罗牌。"""
        result = self.create_tarot_result(event)
        async for item in result:
            yield item

    async def create_tarot_result(self, event: AstrMessageEvent):
        if self.tarot_dict is None:
            self.tarot_dict = load_tarot()

        text_now, tarot_image_path = choose_tarot(self.tarot_dict)
        if not tarot_image_path.exists():
            yield event.plain_result(f"塔罗牌图片不存在：{tarot_image_path.name}")
            return

        text_image_path = self.cache_dir / "tarot_text.jpg"
        text_to_image(text_now, text_image_path)

        yield event.chain_result(
            [
                Comp.Image.fromFileSystem(str(text_image_path)),
                Comp.Image.fromFileSystem(str(tarot_image_path)),
            ]
        )

    async def terminate(self):
        logger.info("Tataru AstrBot plugin terminated.")
