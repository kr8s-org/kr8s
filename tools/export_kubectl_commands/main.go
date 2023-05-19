package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"
	"k8s.io/kubectl/pkg/cmd"
)

func main() {
	// Output the command hierarchy to a text file
	err := exportCommandHierarchy(cmd.NewDefaultKubectlCommand(), "command_hierarchy.txt")
	if err != nil {
		fmt.Printf("Failed to export command hierarchy: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("Command hierarchy exported successfully!")
}

func exportCommandHierarchy(cmd *cobra.Command, outputFile string) error {
	file, err := os.Create(outputFile)
	if err != nil {
		return err
	}
	defer file.Close()

	exportSubcommands(cmd, "", file)
	return nil
}

func exportSubcommands(cmd *cobra.Command, prefix string, writer *os.File) {
	name := strings.Fields(cmd.Use)
	full := strings.TrimSpace(fmt.Sprintf("%s %s", prefix, name[0]))
	fmt.Fprintf(writer, "%s\n", full)

	subCmds := cmd.Commands()
	if len(subCmds) > 0 {
		for _, subCmd := range subCmds {
			exportSubcommands(subCmd, full, writer)
		}
	}
}
