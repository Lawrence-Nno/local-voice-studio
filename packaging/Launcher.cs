using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

class Launcher
{
    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string python = Path.Combine(root, "runtime", "turbo", "pythonw.exe");
            if (!File.Exists(python))
                throw new Exception("The bundled runtime is missing. Keep the entire Local Voice Studio folder together.");
            var start = new ProcessStartInfo(python, "-E -s -m app.desktop" +
                (args.Length == 1 && args[0] == "--check" ? " --check" : ""));
            start.WorkingDirectory = root;
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            // Keep unrelated Python installations from influencing this copy.
            start.EnvironmentVariables.Remove("PYTHONHOME");
            start.EnvironmentVariables.Remove("PYTHONPATH");
            Process.Start(start);
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "Local Voice Studio cannot start", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
