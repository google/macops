///
/// Functions for managing subprocesses.
///

#ifndef RUN_IT_PROCESS_H_
#define RUN_IT_PROCESS_H_

#include <syslog.h>
#include <sys/time.h>

///
/// Convert a struct timeval to a double (secs.usec)
/// Args:
///   tv: a struct timeval
/// Returns:
///   double
///
double TimevalToDouble(struct timeval tv);

///
/// Create a string representation of the command, pid, status, elapsed time and
///  resources used by this command.
/// Args:
///   args: NSArray containing the path and arguments of the command
///   pid: The process id of the child process
///   status: The exit status of the command
///   start_time: The time the subprocess started executing
///   end_time: the time the subprocess finished
///   rusage: the rusage struct for the subprocess
/// Returns:
///   An NSString describing the process.
///
NSString *Description(NSArray *args, pid_t pid, int status,
                      struct timeval startTime, struct timeval endTime,
                      struct rusage rusage);


///
/// Run a command, specified by argv
/// Args:
///   argv: NULL terminated array of cstrings to pass to execvp
///   pid: return parameter, contains the pid of the subprocess
/// Returns:
///   bool: the success of the underlying fork() call.
///
bool LaunchProcess(const char **argv, pid_t *pid);

///
/// Wait for subprocess to exit and collect status and rusage
/// Arguments:
///   pid: The pid of the subprocess to wait on
///   status: return parameter, contains exit status of process
///   rusage: return parameter, contains rusage struct for the process
/// Returns:
///   bool: success of underlying wait4 call
///
bool WaitForExit(pid_t child_pid, int *status, struct rusage *rusage);

#endif  // OPS_MACOPS_UTILITIES_RESOURCE_REPORTING_RUN_IT_PROCESS_H_
