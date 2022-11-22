package de.offis.mosaik.api.utils.generics;

import de.offis.mosaik.api.SimProcess;
import de.offis.mosaik.api.Simulator;
import org.apache.commons.lang3.SystemUtils;
import org.junit.Test;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * @author Alexander Hill
 */
public class ApplicationExampleTest {

    @Test
    public void testSingleModelIntegration() throws Throwable {
        Process pythonProcess = startPythonMosaik("SingleModel.xml");
        Simulator sim = new ExampleModelSim();
        String[] ipaddr = {"127.0.0.1:5878", "server"};
        SimProcess.startSimulation(ipaddr, sim);
        assert pythonProcess.waitFor() == 0: "Something went wrong when executing the python test";
    }

    @Test
    public void testMultiModelIntegration() throws Throwable {
        Process pythonProcess = startPythonMosaik("MultiModel.xml");
        Simulator sim = new MultiModelExampleSim();
        String[] ipaddr = {"127.0.0.1:5878", "server"};
        SimProcess.startSimulation(ipaddr, sim);
        assert pythonProcess.waitFor() == 0: "Something went wrong when executing the python test";
    }

    private static Process startPythonMosaik(String testName) throws InterruptedException, IOException {
        Path path = Paths.get(".");
        if (SystemUtils.IS_OS_WINDOWS) {
            assert new ProcessBuilder().directory(path.toFile()).command("pip", "install", "virtualenv").start().waitFor() == 0;
            assert new ProcessBuilder().directory(path.toFile()).command("virtualenv", "-p", "python3", "test_env").start().waitFor() == 0;
            assert new ProcessBuilder().directory(path.toFile()).command(".\\test_env\\Scripts\\activate.bat").start().waitFor() == 0;
            assert new ProcessBuilder().directory(path.toFile()).command("pip", "install", "-r", "src/test/python/requirements.txt").start().waitFor() == 0;
        } //else {
        //assert new ProcessBuilder().directory(path.toFile()).command(".", "test_env/bin/activate").start().waitFor() == 0;
        //}
        return new ProcessBuilder().directory(path.toFile()).command("python", "-m", "pytest", "--junitxml", "build/test-results/test/" + testName)
                .redirectError(ProcessBuilder.Redirect.INHERIT)
                .redirectOutput(ProcessBuilder.Redirect.INHERIT)
                .redirectInput(ProcessBuilder.Redirect.INHERIT)
                .start();
    }
}
