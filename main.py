# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "nicegui",
#     "sqlite3",
#     "qrcode",
# ]
# ///
import base64
import logging
import pathlib
import sqlite3
import uuid
from io import BytesIO
from typing import Dict, List

import qrcode
from nicegui import ui

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# SQLite setup
DB_NAME = "meme_rankings.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS meme_ratings
                 (user_id TEXT, meme_name TEXT, rating INTEGER)""")
    conn.commit()
    conn.close()


init_db()


class MemeRanker:
    def __init__(self):
        self.memes: List[Dict] = self.get_memes()
        self.user_rating: dict[int, int] = {}
        self.current_meme_index = 0
        self.total_memes = len(self.memes)
        self.rating_buttons = []
        logger.info(f"MemeRanker initialized with {self.total_memes} memes")

    def get_memes(self):
        memes = []
        meme_dir = pathlib.Path("memes")
        if not meme_dir.exists() or not meme_dir.is_dir():
            logger.error("The 'memes' directory does not exist.")
            raise FileNotFoundError("The 'memes' directory does not exist.")

        for image in meme_dir.iterdir():
            if image.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif"]:
                memes.append({"name": image.stem, "url": str(image), "scores": []})

        if not memes:
            logger.error("No image files found in the 'memes' directory.")
            raise FileNotFoundError("No image files found in the 'memes' directory.")

        logger.info(f"Loaded {len(memes)} memes from the directory")
        return memes[:5]

    def rate_meme(self, score: int, user_id: str):
        logger.info(f"Rating meme {self.current_meme_index} with score {score}")
        self.user_rating[self.current_meme_index] = score
        self.memes[self.current_meme_index]["scores"].append(score)
        self.save_rating_to_db(
            self.memes[self.current_meme_index]["name"], score, user_id
        )
        self.next_meme()

    def save_rating_to_db(self, meme_name: str, rating: int, user_id: str):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "INSERT INTO meme_ratings (user_id, meme_name, rating) VALUES (?, ?, ?)",
            (user_id, meme_name, rating),
        )
        conn.commit()
        conn.close()
        logger.info(
            f"Saved rating to database: User {user_id}, Meme {meme_name}, Rating {rating}"
        )

    def update_meme(self):
        meme = self.memes[self.current_meme_index]
        meme_image.set_source(meme["url"])
        meme_name.set_text(meme["name"])
        progress.set_value(self.current_meme_index / self.total_memes)
        progress_label.set_text(f"{self.current_meme_index + 1} / {self.total_memes}")
        self.update_button_colors()
        logger.info(f"Updated to meme {self.current_meme_index}: {meme['name']}")

    def show_results(self):
        logger.info("Showing results page")
        ui.open("/results")

    def reset(self):
        logger.info("Resetting MemeRanker")
        self.current_meme_index = 0
        self.user_rating.clear()
        for meme in self.memes:
            meme["scores"] = []
        self.update_meme()
        ui.open("/")

    def next_meme(self):
        self.current_meme_index = (self.current_meme_index + 1) % self.total_memes
        self.update_meme()
        if self.current_meme_index == 0:
            logger.info("Reached the end of memes, showing results")
            self.show_results()

    def prev_meme(self):
        self.current_meme_index = (self.current_meme_index - 1) % self.total_memes
        self.update_meme()

    def update_button_colors(self):
        user_rating = self.user_rating.get(self.current_meme_index)
        for i, button in enumerate(self.rating_buttons, 1):
            if user_rating and i == user_rating:
                button.style("background-color: #4CAF50; color: white;")
            else:
                button.style("background-color: #f0f0f0; color: black;")
        logger.debug(f"Updated button colors for meme {self.current_meme_index}")


ranker = MemeRanker()


def generate_qr_code(url: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)  # Removed the format argument
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"


@ui.page("/")
async def init_page():
    user_id = str(uuid.uuid4())
    logger.info(f"New user connected: {user_id}")

    # url = await show_url()

    # external_url = f"http://{ui.run.host}:{ui.run.port}"
    # qr_code = generate_qr_code(external_url)

    with ui.column().classes("w-full h-screen items-center justify-center"):
        ui.label("Welcome to Meme Ranker!").classes("text-2xl mb-4")

        async def show_url():
            logger.info("Showing URL")
            a = await ui.run_javascript("new URL(window.location.href)")
            qr_code = generate_qr_code(str(a))
            ui.image(qr_code).classes("w-64 h-64 mb-4")
            logger.info("Showed URL", a)

            ui.label(a)

        ui.button("Show QR code", on_click=show_url)
        # ui.label(f"Scan the QR code or visit: {external_url}").classes("mb-4")
        ui.button("Start Rating", on_click=lambda: ui.open(f"/rate/{user_id}")).classes(
            "text-xl"
        )


@ui.page("/rate/{user_id}")
def rating_page(user_id: str):
    logger.info(f"Rendering rating page for user {user_id}")
    with ui.column().classes("w-full h-screen p-4"):
        with ui.row().classes(
            "w-full md:w-1/3 p-4 flex flex-col justify-center items-center"
        ):
            ui.label("Rate the Meme").classes("text-h4 mb-4 text-center")
            global meme_name, progress, progress_label
            meme_name = ui.label(ranker.memes[0]["name"]).classes(
                "text-xl mb-4 text-center"
            )
            # progress = ui.linear_progress(value=0).classes("w-full mb-2")
            # progress_label = ui.label(f"1 / {ranker.total_memes}").classes(
            #     "mb-4 text-center"
            # )
            with ui.row().classes("gap-1 w-full"):
                ranker.rating_buttons = [
                    ui.button(
                        str(i), on_click=lambda _, i=i: ranker.rate_meme(i, user_id)
                    ).classes()
                    for i in range(1, 6, 1)
                ]
            with ui.row().classes("mt-4 gap-2 w-full"):
                ui.button("Previous", on_click=ranker.prev_meme).classes("w-1/3")
                ui.button("Next", on_click=ranker.next_meme).classes("w-1/3")

        with ui.row().classes(
            "w-full md:w-1/2 bg-gray-100 flex items-center justify-center mt-4 md:mt-0"
        ):
            global meme_image
            meme_image = ui.image(ranker.memes[0]["url"]).classes(
                "max-w-full max-h-full object-contain"
            )

    ranker.update_button_colors()


@ui.page("/results")
def ranking_page():
    logger.info("Rendering results page")
    with ui.column().classes("w-full h-screen p-4 flex flex-col items-center"):
        ui.label("Meme Rankings").classes("text-h3 mb-4 text-center")
        sorted_memes = sorted(
            ranker.memes,
            key=lambda m: sum(m["scores"]) / len(m["scores"]) if m["scores"] else 0,
            reverse=True,
        )
        with ui.row().classes("flex-grow overflow-auto w-full max-w-2xl"):
            for i, meme in enumerate(sorted_memes):
                avg_score = (
                    sum(meme["scores"]) / len(meme["scores"]) if meme["scores"] else 0
                )
                ui.label(
                    f"{i+1}. {meme['name']} - Average Score: {avg_score:.2f}"
                ).classes("text-lg mb-2 text-center w-full")
        ui.button("Start Over", on_click=ranker.reset).classes("mt-4 w-full max-w-xs")


ui.query(".nicegui-content").classes("w-full")
ui.query(".q-page").classes("flex")

with ui.header():
    ui.label("HEADER")
with ui.footer():
    ui.label("FOOTER")

ui.label("CONTENT")
ui.aggrid({}).classes("flex-grow")
logger.info("Starting the application")


ui.run()
