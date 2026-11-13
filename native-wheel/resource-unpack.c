#include <stdint.h>
#include <stddef.h>

void decode(uint8_t *data, size_t size, uint64_t nonce) {
    const uint32_t key[4] = {1923467295U, 456984297U, (uint32_t)-129215849, (uint32_t)-1636392885};
    for (size_t off = 0; off < size; off += 8) {
        uint64_t block = nonce + off / 8;
        uint32_t left = block >> 32, right = block, sum = 0;
        for (int round = 0; round < 32; ++round) {
            left += (((right << 4) ^ (right >> 5)) + right) ^ (key[sum & 3] + sum);
            sum += 0x9e3779b9U;
            right += (((left << 4) ^ (left >> 5)) + left) ^ (key[(sum >> 11) & 3] + sum);
        }
        for (unsigned i = 0; i < 8 && off + i < size; ++i)
            data[off + i] ^= (i < 4 ? left : right) >> ((3 - (i & 3)) * 8);
    }
}
