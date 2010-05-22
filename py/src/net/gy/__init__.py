import logging;
import logging.handlers;
import logging.config;

logging.config.fileConfig("conf/logging.conf");
log = logging.getLogger("net.gy");