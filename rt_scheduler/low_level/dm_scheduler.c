#include "dm_scheduler.h"

#include <math.h>
#include <stddef.h>
#include <stdlib.h>

static int compare_deadline(const double *deadline, const int *indices, size_t a, size_t b) {
    double da = deadline[indices[a]];
    double db = deadline[indices[b]];
    if (da < db) {
        return -1;
    }
    if (da > db) {
        return 1;
    }
    return 0;
}

int dm_response_time_feasible(const double *execution,
                              const double *period,
                              const double *deadline,
                              size_t count) {
    if (!execution || !period || !deadline) {
        return 0;
    }
    if (count == 0) {
        return 1;
    }

    int *order = (int *)malloc(sizeof(int) * count);
    if (!order) {
        return 0;
    }
    for (size_t i = 0; i < count; ++i) {
        order[i] = (int)i;
    }

    for (size_t i = 0; i + 1 < count; ++i) {
        size_t min_idx = i;
        for (size_t j = i + 1; j < count; ++j) {
            if (compare_deadline(deadline, order, j, min_idx) < 0) {
                min_idx = j;
            }
        }
        if (min_idx != i) {
            int tmp = order[i];
            order[i] = order[min_idx];
            order[min_idx] = tmp;
        }
    }

    const double EPS = 1e-9;

    for (size_t i = 0; i < count; ++i) {
        int idx = order[i];
        double response = execution[idx];
        double limit = deadline[idx];

        while (1) {
            double interference = 0.0;
            for (size_t j = 0; j < i; ++j) {
                int hp = order[j];
                double hp_period = period[hp];
                if (hp_period <= 0.0) {
                    free(order);
                    return 0;
                }
                interference += ceil(response / hp_period) * execution[hp];
            }
            double next_response = execution[idx] + interference;
            if (next_response > limit + EPS) {
                free(order);
                return 0;
            }
            if (fabs(next_response - response) < EPS) {
                break;
            }
            response = next_response;
            if (response > limit + EPS) {
                free(order);
                return 0;
            }
        }
    }

    free(order);
    return 1;
}
