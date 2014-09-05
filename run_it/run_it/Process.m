//
// Functions for managing subprocesses.
//

#include "Process.h"

double TimevalToDouble(struct timeval tv) {
  return ((double)tv.tv_sec + (((double)tv.tv_usec)/1000000.0));
}


NSString *Description(NSArray *args, pid_t pid, int status,
                      struct timeval startTime, struct timeval endTime,
                      struct rusage rusage) {
  char startTimeBuf[26];  //"YYYY-MM-DDTHH:MM:SS+hhmm"
  struct tm tm;
  localtime_r(&startTime.tv_sec, &tm);
  strftime(startTimeBuf, sizeof(startTimeBuf), "%FT%T%z", &tm);

  return [NSString stringWithFormat:@"cmd=\"%@\" "
          "pid=%d "
          "status=%d "
          "starttime=%s "
          "elapsed=%lf "
          "user=%lf "
          "system=%lf "
          "maxrss=%ld "
          "page_reclaims=%ld "
          "page_faults=%ld "
          "swaps=%ld "
          "blocked_in=%ld "
          "blocked_out=%ld "
          "msg_sent=%ld "
          "msg_received=%ld "
          "context_switches=%ld "
          "involuntary_context_switches=%ld "
          "signals=%ld"
          "\n",
          [args componentsJoinedByString:@" "],
          pid,
          WEXITSTATUS(status),
          startTimeBuf,
          TimevalToDouble(endTime) - TimevalToDouble(startTime),
          TimevalToDouble(rusage.ru_utime),
          TimevalToDouble(rusage.ru_stime),
          rusage.ru_maxrss,
          rusage.ru_minflt,
          rusage.ru_majflt,
          rusage.ru_nswap,
          rusage.ru_inblock,
          rusage.ru_oublock,
          rusage.ru_msgsnd,
          rusage.ru_msgrcv,
          rusage.ru_nvcsw,
          rusage.ru_nivcsw,
          rusage.ru_nsignals];

}

bool LaunchProcess(const char **argv, pid_t *pid) {
  pid_t childPid = fork();
  if (childPid == -1) {
    perror("fork failed");
    return false;
  } else if (childPid == 0) {  // in the child
    execvp(argv[0], (char **)argv);
    perror(argv[0]);
    exit(1);
  }
  *pid = childPid;
  return true;
}

bool WaitForExit(pid_t childPid, int *status, struct rusage *rusage) {
  pid_t pid = 0;
  do {
    pid = wait4(childPid, status, 0, rusage);  // collect the status and rusage
    if (pid == -1 && errno == EINTR) {
      pid = 0;
      continue;
    }
    if (pid != -1 && WIFSTOPPED(status)) {
      pid = 0;
      continue;
    }
    if (pid == -1) {
      perror("wait4");
      return false;
    }
  } while(pid != childPid && pid != -1);
  return true;
}
