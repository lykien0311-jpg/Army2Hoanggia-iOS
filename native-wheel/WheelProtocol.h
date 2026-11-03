#ifndef AG_WHEEL_PROTOCOL_H
#define AG_WHEEL_PROTOCOL_H
#include <stddef.h>
#include <stdint.h>
#define AG_MAX_ROWS 20
#define AG_NAME 256
#define AG_TEXT 1024
#define AG_MIN_STAKE INT64_C(1000000)
#define AG_MAX_STAKE INT64_C(50000000)
typedef struct { char name[AG_NAME]; int64_t amount; uint8_t own; } AGRow;
typedef struct {
    int version, status, count, tax, page, rows, hasResult, resultTax;
    char message[AG_TEXT], winner[AG_NAME];
    int64_t ack, serverTime, round, starts, ends, total, own, balance, pending;
    int64_t resultRound, resultPool, resultPrize, resultStake;
    AGRow entries[AG_MAX_ROWS];
} AGSnapshot;
int AGParse(const uint8_t *data, size_t length, AGSnapshot *out);
size_t AGPoll(uint8_t out[8], int32_t page);
size_t AGBet(uint8_t out[28], int64_t round, int64_t nonce, int64_t amount);
const char *AGValidateBet(const AGSnapshot *s, int64_t serverNow, int64_t amount);
#endif
