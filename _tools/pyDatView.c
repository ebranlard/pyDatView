/* Launch pyDatView
 *
 * Four cases are considered, by order of priority:
 *   1. The user runs /PATH/TO/REPO/_tools/pyDatView.exe: in that case we call:
 *         `pythonw /PATH/TO/REPO/pyDataView.py [ARGS]`   (no import)
 *   2. The user runs /PATH/TO/INSTALL/pyDatView.exe: in that case we assume that
 *      a python executable is located in `/PATH/TO/INSTALL/Python/`, and we run:
 *        `/PATH/TO/INSTALL/PYTHON/pythonw.exe -c "import pydatview; pydatview.show(filenames=[ARGS])"
 *   3. The user runs /RANDOMPATH/pyDatView.exe: in that case we assume that the 
 *       python installation path  is C:\Users\%USERNAME%\AppData\Local\pyDataView\Python .
 *       If a pythonw is found there we follow the same command as 2.
 *   4. The user runs /RANDOMPATH/pyDatView.exe: in that case we assume that the 
 *       installation path is in the environmental variable PYDATPATH.
 *       If a pythonw is found there we follow the same command as 2.
 *
 * */
#define _WIN32_WINNT 0x0500
#define MAX 1024
//#define IDI_ICON_1            102

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>   // stat
#include <stdbool.h>    // bool type


#include <windows.h>
#pragma comment(lib,"User32.lib") // for static linking and using ShowWindow


/* True if file exists */
bool file_exists (char *filename) {
  struct stat   buffer;   
  return (stat (filename, &buffer) == 0);
}

/* Returns path of current executable */
char* getpath()
{
 TCHAR path[MAX];
 DWORD length;
 length = GetModuleFileName(NULL, path, 1000);
 char *result = malloc(length+ 1); // +1 for the null-terminator
 int c =0 ;
 while (path[c] != '\0') {
     result[c] = path[c] ;
     c++;
 }
 result[c] = '\0';
 //char *result = path;
 return result;
}


/* Concatenate two strings */
char* concat(const char *s1, const char *s2)
{
    char *result = malloc(strlen(s1) + strlen(s2) + 1); // +1 for the null-terminator
    strcpy(result, s1);
    strcat(result, s2);
    return result;
}

/* Concatenate string2 to string1 */
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


/* Launch pydatview using local pythonw and command line arguments*/
int main (int argc, char** argv) {
    char wd[MAX];
    char args[MAX]="";
    char fullCommand[MAX]="";
    char path [MAX_PATH]="";
    char pydatpy[MAX_PATH]="";
    char pythonwpath0[MAX_PATH]="";
    char pythonwpath1[MAX_PATH]="";
    char pythonwpath2[MAX_PATH]="";
    char pythonwpath3[MAX_PATH]="";
    char pythonwpath4[MAX_PATH]="";
    char* pfullCommand ;
    bool useImport = true;
    int index=0;

    // --- Hidding window
    HWND hWnd = GetConsoleWindow();
    //ShowWindow( hWnd, SW_MINIMIZE );  //won't hide the window without SW_MINIMIZE
    ShowWindow( hWnd, SW_HIDE );

    // --- Get user name (for AppData path)
    char* user = getenv("USERNAME");
    printf("Username   : %s\n", user);

    // --- Executable path
    char * exename = getpath();
    printf("Exe name   : %s\n", exename);
    char *exedir = exename;
    exedir[strlen(exedir) - 13]  = '\0'; // remove pyDatView.exe from path
    char parentdir[7];
    strncpy(parentdir, &exedir[strlen(exedir)-7],6);
    printf("Exe dir    : %s\n", exedir);
    printf("Exe dir-7  : %s\n", parentdir);

    // --- Current directory
    wd[MAX-1] = '\0';
    if(getcwd(wd, MAX-1) == NULL) {
        printf ("[WARN] Can not get current working directory\n");
        wd[0] = '.';
    }
    printf("Current Dir: %s\n", wd);

    // --- Get PYDATPATH if defined as env variable
    char* pydatpath = getenv("PYDATPATH");
    if (pydatpath) {
        printf("PYDATPATH  : %s\n", pydatpath);
    }else{
        printf("PYDATPATH  : (environmental variable not set)\n");
    } 

    // --- Pythonw path (assuming it's in system path)
    concatenate(pythonwpath1, "pythonw ");
    printf("Pythonw1   : %s\n", pythonwpath1);


    // --- Pythonw path (assuming close to current executable)
    concatenate(pythonwpath2, exedir);
    concatenate(pythonwpath2,"Python\\pythonw.exe");
    printf("Pythonw2   : %s\n", pythonwpath2);

    // --- Pythonw path (assuming user installed in AppData)
    concatenate(pythonwpath3,"C:\\Users\\");
    concatenate(pythonwpath3,user);
    concatenate(pythonwpath3,"\\AppData\\Local\\pyDatView\\Python\\pythonw.exe");
    printf("Pythonw3   : %s\n", pythonwpath3);

    // --- Pythonw path (using PYDATPATH env variable)
    if (pydatpath) {
        concatenate(pythonwpath4, pydatpath);
        concatenate(pythonwpath4,"\\Python\\pythonw.exe");
        printf("Pythonw4   : %s\n", pythonwpath4);
    }



    // --- Selecting pythonw path that exist
    if (strcmp(parentdir,"_tools")==0) {
        exedir[strlen(exedir) - 7]  = '\0'; // remove pyDatView.exe from path
        printf("Repo dir   : %s\n", exedir);
        concatenate(pythonwpath0, pythonwpath1);
        useImport =false;
        printf(">>> Using Pythonw1\n");

    } else if (file_exists(pythonwpath2)) {
        concatenate(pythonwpath0, pythonwpath2);
        printf(">>> Using Pythonw2\n");

    } else if (file_exists(pythonwpath3)) {
        concatenate(pythonwpath0, pythonwpath3);
        printf(">>> Using Pythonw3\n");

    } else if (file_exists(pythonwpath4)) {
        concatenate(pythonwpath0, pythonwpath4);
        printf(">>> Using Pythonw4\n");

    } else {
        ShowWindow( hWnd, SW_RESTORE);
        printf("\n");
        printf("[ERROR] Cannot find pythonw.exe. Try the following options: \n");
        printf("        - place the program at the root of the installation directory\n");
        printf("        - rename the program 'pyDatView.exe' \n");
        printf("        - define the environmental variable PYDATPATH to the root install dir. \n");
        printf("   If none of these options work. Contact the developper with the above outputs'\n");
        printf("\n");
        printf("Press any key to close this window\n");
        getchar();
        return -1;
    }

    // --- Convert List of argumenst to python list of string or space separated string
    int i;
    if (useImport) {
        concatenate(args, "[");
        for(i = 1; i <= argc-1; i++) {
            concatenate(args, "'");
            // replacing slashes
            index=0;
            while(argv[i][index])
            {     
                 if(argv[i][index] == '\\')
                    argv[i][index] = '/';
                 else
                    index++;
            }
            concatenate(args, argv[i]);
            concatenate(args, "'");
            if (i<argc-1) {
                concatenate(args, ",");
            }
        }
        concatenate(args, "]");
    } else {
        for(i = 1; i <= argc-1; i++) {
            concatenate(args, "\"");
            concatenate(args, argv[i]);
            concatenate(args, "\"");
            concatenate(args, " ");
        }
    }
    printf("Arguments  : %s\n", args);

    // --- Forming full command
    if (useImport) {
        concatenate(fullCommand, pythonwpath0);
        concatenate(fullCommand, " -c \"import pydatview; pydatview.show(filenames=");
        concatenate(fullCommand, args);
        concatenate(fullCommand, ");\"");
    } else { 
        concatenate(pydatpy, exedir);
        concatenate(pydatpy, "\\pyDatView.py ");
        concatenate(fullCommand, pythonwpath0);
        concatenate(fullCommand, pydatpy);
        concatenate(fullCommand, args);
    }
    printf("Command    : %s\n", fullCommand);
    system(fullCommand);
    
    //printf("Press any key\n");
    //getchar();

    return 0;
}
