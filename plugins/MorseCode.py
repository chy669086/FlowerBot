from alicebot import Plugin
from DuelFrontend import to_text


# 字母、数字和标点符号对应的莫斯电码
TO_MORSE = {'#': '#','A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.', '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.', '!': '-.-.--', '/': '-..-.', '(': '-.--.', ')': '-.--.-', '&': '.-...', ':': '---...', ';': '-.-.-.', '=': '-...-', '+': '.-.-.', '-': '-....-', '_': '..--.-', '"': '.-..-.', '$': '...-..-', '@': '.--.-.', '@': '.--.-.', ' ': '/'}

# 莫斯电码对应的字母、数字和标点符号
FROM_MORSE = {v: k for k, v in TO_MORSE.items()}

def translate_to_morse(english_text):
    english_text = english_text.upper()
    morse_code = ''

    for char in english_text:
        morse_code += TO_MORSE.get(char, '#') + ' '

    return morse_code

def translate_from_morse(morse_code):
    words = morse_code.split(' / ')
    translated_words = []

    for word in words:
        letters = word.split(' ')
        translated_word = ''.join(FROM_MORSE.get(letter, '') for letter in letters)
        translated_words.append(translated_word)

    return ' '.join(translated_words)


class MorseCode(Plugin):
    async def handle(self):
        message_chain = self.event.message.as_message_chain()
        text = to_text(message_chain)
        if text.startswith('/morse'):
            english_text = text[7:]
            morse_code = translate_to_morse(english_text)
            await self.event.reply(morse_code)
        elif text.startswith('/english'):
            morse_code = text[9:]
            english_text = translate_from_morse(morse_code)
            await self.event.reply(english_text)

    async def rule(self) -> bool:
        try:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            return text.startswith('/morse') or text.startswith('/english')
        except:
            return False