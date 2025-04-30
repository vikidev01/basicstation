#ifndef _LORAGW_STATIONLOG_H
#define _LORAGW_STATIONLOG_H

#if defined(STATIONLOG)

#undef DEBUG_PRINTF
#undef DEBUG_MSG

enum { XDEBUG=0, DEBUG, VERBOSE, INFO, NOTICE, WARNING, ERROR, CRITICAL };
extern void log_hal (uint8_t level, const char* fmt, ...);
#define ERROR_PRINTF(fmt, ...)     log_hal(ERROR  , "[%s:%d] "fmt, __FUNCTION__, __LINE__, ## __VA_ARGS__)
#define INFO_PRINTF(fmt, ...)      log_hal(INFO   , "[%s:%d] "fmt, __FUNCTION__, __LINE__, ## __VA_ARGS__)
#define DEBUG_PRINTF(fmt, ...)     log_hal(XDEBUG , "[%s:%d] "fmt, __FUNCTION__, __LINE__, ## __VA_ARGS__)
#define DEBUG_MSG(str)             log_hal(XDEBUG , "[%s:%d] %s", __FUNCTION__, __LINE__, str)
#define XDEBUG_PRINTF(fmt, ...)    log_hal(XDEBUG , "[%s:%d] "fmt, __FUNCTION__, __LINE__, ## __VA_ARGS__)
#define XDEBUG_MSG(str)            log_hal(XDEBUG , "[%s:%d] %s", __FUNCTION__, __LINE__, str)

#else // !defined(STATIONLOG)

#define ERROR_PRINTF(fmt, ...)     DEBUG_PRINTF(fmt, ## __VA_ARGS__)
#define INFO_PRINTF(fmt, ...)      DEBUG_PRINTF(fmt, ## __VA_ARGS__)
#define XDEBUG_PRINTF(fmt, ...)    DEBUG_PRINTF(fmt, ## __VA_ARGS__)
#define XDEBUG_MSG(str)            DEBUG_MSG(str)
#endif

#endif
