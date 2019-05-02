#define _WIN32_WINNT 0x0500
#define MAX 1024

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <windows.h>
#pragma comment(lib,"User32.lib") // for static linking and using ShowWindow

char* concat(const char *s1, const char *s2)
{
    char *result = malloc(strlen(s1) + strlen(s2) + 1); // +1 for the null-terminator
    strcpy(result, s1);
    strcat(result, s2);
    return result;
}

void concatenate(char p[], char q[]) {
   int c, d;
   c = 0;
   while (p[c] != '\0') {
      c++;      
   }
   d = 0;
   while (q[d] != '\0') {
      p[c] = q[d];
      d++;
      c++;    
   }
   p[c] = '\0';
}


int main (int argc, char** argv) {
    char mainCommand[] = "\\Python\\pythonw.exe -c \"import pydatview; pydatview.show();\"";
    char wd[MAX];
    char args[MAX]="";
    char fullCommand[MAX]="";
    char path [MAX_PATH];
    char* pfullCommand ;

    // --- Hidding window
    HWND hWnd = GetConsoleWindow();
    ShowWindow( hWnd, SW_MINIMIZE );  //won't hide the window without SW_MINIMIZE
    ShowWindow( hWnd, SW_HIDE );

    // --- List of argumenst to python list of string
    int i;
    concatenate(args, "[");
    for(i = 1; i <= argc-1; i++) {
        concatenate(args, "'");
        concatenate(args, argv[i]);
        concatenate(args, "'");
        if (i<argc-1) {
            concatenate(args, ",");
        }
    }
    concatenate(args, "]");
    printf("Arguments: %s\n", args);


    // --- Current directory
    wd[MAX-1] = '\0';
    if(getcwd(wd, MAX-1) == NULL) {
        printf ("[WARN] Can not get current working directory\n");
        wd[0] = '.';
    }
    printf("Current Dir : %s\n", wd);

    // --- Forming full command
    concatenate(fullCommand, wd);
    concatenate(fullCommand, "\\Python\\pythonw.exe -c \"import pydatview; pydatview.show(filenames=");
    concatenate(fullCommand, args);
    concatenate(fullCommand, ");\"");
    printf("Full command: %s\n", fullCommand);
    system(fullCommand);
    
    //printf("Main command: %s\n", mainCommand);
    //pfullCommand=concat(wd,mainCommand);
    //printf("Full command: %s\n", pfullCommand);
    //system(pfullCommand);
    free(pfullCommand);
    return 0;
}
