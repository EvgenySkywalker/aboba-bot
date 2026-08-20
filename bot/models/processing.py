from dataclasses import dataclass

from telegram import Update, PhotoSize

@dataclass
class ProcessPayload:
    update: Update
    photos: list[PhotoSize]
