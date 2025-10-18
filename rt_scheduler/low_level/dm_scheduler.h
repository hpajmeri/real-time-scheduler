#ifndef DM_SCHEDULER_H
#define DM_SCHEDULER_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

int dm_response_time_feasible(const double *execution,
                              const double *period,
                              const double *deadline,
                              size_t count);

#ifdef __cplusplus
}
#endif

#endif /* DM_SCHEDULER_H */
