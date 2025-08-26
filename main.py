from logger import get_logger
import bot

log = get_logger('main')

if __name__ == '__main__':
    log.info('Starting bot...')
    bot.run()
