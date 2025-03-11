
# Software Supply Chain Report of INRIA/spoon - v11.1.0

## Enabled Checks
The following checks were specifically requested:

- Source Code
- Release Tags
- Deprecated
- Provenance
- Code Signature
- Aliased Package

---


<details>
    <summary>How to read the results :book: </summary>
    
 Dirty-waters has analyzed your project dependencies and found different categories for each of them:

    
 - ⚠️⚠️⚠️ : high severity 

    
 - ⚠️⚠️: medium severity 

    
 - ⚠️: low severity 

</details>
        

 ### Total packages in the supply chain: 403


:heavy_exclamation_mark: Packages with no source code URL (⚠️⚠️⚠️): 2

:no_entry: Packages with repo URL that is 404 (⚠️⚠️⚠️): 1

:wrench: Packages with inaccessible GitHub tag (⚠️⚠️): 55

:lock: Packages without code signature (⚠️⚠️): 14


<details>
    <summary>Other info:</summary>
    
- Source code repo is not hosted on GitHub:  87

    This could be due, for example, to the package being hosted on a different platform.

    This does not mean that the source code URL is invalid.

    However, for non-GitHub repositories, not all checks can currently be performed.

|   index | package_name                                                         | github_url                                                                               | command         |
|--------:|:---------------------------------------------------------------------|:-----------------------------------------------------------------------------------------|:----------------|
|       1 | `org.ow2.asm:asm@9.6`                                                | https://gitlab.ow2.org/asm/asm/                                                          | resolve-plugins |
|       2 | `org.eclipse.aether:aether-spi@1.0.0.v20140518`                      | http://git.eclipse.org/c/aether/aether-core.git/tree/aether-spi/                         | resolve-plugins |
|       3 | `org.eclipse.aether:aether-impl@1.0.0.v20140518`                     | http://git.eclipse.org/c/aether/aether-core.git/tree/aether-impl/                        | resolve-plugins |
|       4 | `org.eclipse.aether:aether-api@1.0.0.v20140518`                      | http://git.eclipse.org/c/aether/aether-core.git/tree/aether-api/                         | resolve-plugins |
|       5 | `org.eclipse.sisu:org.eclipse.sisu.plexus@0.3.5`                     | http://git.eclipse.org/c/sisu/org.eclipse.sisu.plexus.git/tree/org.eclipse.sisu.plexus/  | resolve-plugins |
|       6 | `javax.annotation:javax.annotation-api@1.2`                          | http://java.net/projects/glassfish/sources/svn/show/tags/javax.annotation-api-1.2        | resolve-plugins |
|       7 | `org.eclipse.sisu:org.eclipse.sisu.inject@0.3.5`                     | http://git.eclipse.org/c/sisu/org.eclipse.sisu.inject.git/tree/org.eclipse.sisu.inject/  | resolve-plugins |
|       8 | `javax.inject:javax.inject@1`                                        | http://code.google.com/p/atinject/source/checkout                                        | resolve         |
|       9 | `aopalliance:aopalliance@1.0`                                        | null object or invalid expression                                                        | resolve-plugins |
|      10 | `com.google.guava:guava@16.0.1`                                      | http://code.google.com/p/guava-libraries/source/browse/guava                             | resolve-plugins |
|      11 | `org.sonatype.plexus:plexus-sec-dispatcher@1.3`                      | No_repo_info_found                                                                       | resolve-plugins |
|      12 | `org.sonatype.plexus:plexus-cipher@1.4`                              | No_repo_info_found                                                                       | resolve-plugins |
|      13 | `org.eclipse.aether:aether-util@1.0.0.v20140518`                     | http://git.eclipse.org/c/aether/aether-core.git/tree/aether-util/                        | resolve-plugins |
|      14 | `commons-io:commons-io@2.6`                                          | https://git-wip-us.apache.org/repos/asf?p=commons-io.git                                 | resolve-plugins |
|      15 | `org.apache.commons:commons-compress@1.20`                           | https://gitbox.apache.org/repos/asf?p=commons-compress.git                               | resolve-plugins |
|      16 | `org.tukaani:xz@1.9`                                                 | https://git.tukaani.org/?p=xz-java.git                                                   | resolve-plugins |
|      17 | `org.codehaus.plexus:plexus-i18n@1.0-beta-10`                        | http://fisheye.codehaus.org/browse/plexus/plexus-components/tags/plexus-i18n-1.0-beta-10 | resolve-plugins |
|      18 | `org.apache.xbean:xbean-reflect@3.7`                                 | http://svn.apache.org/viewvc/geronimo/xbean/tags/xbean-3.7/xbean-reflect                 | resolve-plugins |
|      19 | `com.google.collections:google-collections@1.0`                      | http://code.google.com/p/google-collections/source/browse/                               | resolve-plugins |
|      20 | `org.apache.commons:commons-lang3@3.8.1`                             | https://git-wip-us.apache.org/repos/asf?p=commons-lang.git                               | resolve-plugins |
|      21 | `org.apache.commons:commons-text@1.3`                                | https://git-wip-us.apache.org/repos/asf?p=commons-text.git                               | resolve-plugins |
|      22 | `commons-logging:commons-logging@1.2`                                | http://svn.apache.org/repos/asf/commons/proper/logging/trunk                             | resolve-plugins |
|      23 | `commons-codec:commons-codec@1.11`                                   | http://svn.apache.org/viewvc/commons/proper/codec/trunk                                  | resolve-plugins |
|      24 | `org.apache.velocity:velocity@1.7`                                   | http://svn.apache.org/viewvc/velocity/engine/trunk                                       | resolve-plugins |
|      25 | `commons-lang:commons-lang@2.4`                                      | http://svn.apache.org/viewvc/commons/proper/lang/trunk                                   | resolve-plugins |
|      26 | `org.apache.velocity:velocity-tools@2.0`                             | http://svn.apache.org/repos/asf/velocity/tools/trunk                                     | resolve-plugins |
|      27 | `commons-beanutils:commons-beanutils@1.7.0`                          | null object or invalid expression                                                        | resolve-plugins |
|      28 | `commons-digester:commons-digester@1.8`                              | http://svn.apache.org/repos/asf/jakarta/commons/proper/digester/trunk                    | resolve-plugins |
|      29 | `commons-chain:commons-chain@1.1`                                    | http://svn.apache.org/viewcvs.cgi                                                        | resolve-plugins |
|      30 | `dom4j:dom4j@1.1`                                                    | null object or invalid expression                                                        | resolve-plugins |
|      31 | `oro:oro@2.0.8`                                                      | null object or invalid expression                                                        | resolve-plugins |
|      32 | `commons-collections:commons-collections@3.2.2`                      | http://svn.apache.org/viewvc/commons/proper/collections/trunk                            | resolve-plugins |
|      33 | `javax.servlet:javax.servlet-api@3.1.0`                              | http://java.net/projects/glassfish/sources/svn/show/tags/javax.servlet-api-3.1.0         | resolve-plugins |
|      34 | `org.apache.commons:commons-lang3@3.14.0`                            | https://gitbox.apache.org/repos/asf?p=commons-lang.git                                   | resolve-plugins |
|      35 | `org.apache.commons:commons-text@1.11.0`                             | https://gitbox.apache.org/repos/asf?p=commons-text.git                                   | resolve-plugins |
|      36 | `org.eclipse.jgit:org.eclipse.jgit@5.13.3.202401111512-r`            | https://git.eclipse.org/r/plugins/gitiles/jgit/jgit/org.eclipse.jgit                     | resolve-plugins |
|      37 | `org.eclipse.jgit:org.eclipse.jgit.ssh.apache@5.13.3.202401111512-r` | https://git.eclipse.org/r/plugins/gitiles/jgit/jgit/org.eclipse.jgit.ssh.apache          | resolve-plugins |
|      38 | `commons-io:commons-io@2.11.0`                                       | https://gitbox.apache.org/repos/asf?p=commons-io.git                                     | resolve-plugins |
|      39 | `com.google.code.findbugs:jsr305@2.0.0`                              | http://findbugs.googlecode.com/svn/trunk/                                                | resolve-plugins |
|      40 | `org.ow2.asm:asm@5.0.3`                                              | http://svn.forge.objectweb.org/cgi-bin/viewcvs.cgi/asm/trunk/asm/                        | resolve-plugins |
|      41 | `org.ow2.asm:asm-commons@5.0.3`                                      | http://svn.forge.objectweb.org/cgi-bin/viewcvs.cgi/asm/trunk/asm-commons/                | resolve-plugins |
|      42 | `org.ow2.asm:asm-tree@5.0.3`                                         | http://svn.forge.objectweb.org/cgi-bin/viewcvs.cgi/asm/trunk/asm-tree/                   | resolve-plugins |
|      43 | `commons-lang:commons-lang@1.0`                                      | null object or invalid expression                                                        | resolve-plugins |
|      44 | `de.tototec:de.tototec.cmdoption@0.2.0`                              | http://cmdoption.tototec.de/svn/cmdoption                                                | resolve-plugins |
|      45 | `org.apache.commons:commons-text@1.12.0`                             | https://gitbox.apache.org/repos/asf?p=commons-text.git                                   | resolve-plugins |
|      46 | `commons-io:commons-io@2.15.1`                                       | https://gitbox.apache.org/repos/asf?p=commons-io.git                                     | resolve-plugins |
|      47 | `org.apache.commons:commons-compress@1.26.1`                         | https://gitbox.apache.org/repos/asf?p=commons-compress.git                               | resolve-plugins |
|      48 | `org.ow2.asm:asm@9.7`                                                | https://gitlab.ow2.org/asm/asm/                                                          | resolve-plugins |
|      49 | `org.sonatype.plexus:plexus-build-api@0.0.7`                         | http://svn.sonatype.org/spice/tags/plexus-build-api-0.0.7                                | resolve-plugins |
|      50 | `org.apache.velocity:velocity-engine-core@2.4`                       | https://gitbox.apache.org/repos/asf?p=velocity-engine.git/velocity-engine-core           | resolve-plugins |
|      51 | `org.apache.velocity.tools:velocity-tools-generic@3.1`               | https://gitbox.apache.org/repos/asf?p=velocity-tools.git/velocity-tools-generic          | resolve-plugins |
|      52 | `commons-beanutils:commons-beanutils@1.9.4`                          | http://svn.apache.org/viewvc/commons/proper/beanutils/tags/BEANUTILS_1_9_3_RC3           | resolve-plugins |
|      53 | `org.apache.commons:commons-digester3@3.2`                           | http://svn.apache.org/viewvc/commons/proper/digester/tags/DIGESTER3_3_2_RC2              | resolve-plugins |
|      54 | `org.apache.commons:commons-lang3@3.17.0`                            | https://gitbox.apache.org/repos/asf?p=commons-lang.git                                   | resolve-plugins |
|      55 | `org.apache.commons:commons-compress@1.26.2`                         | https://gitbox.apache.org/repos/asf?p=commons-compress.git                               | resolve-plugins |
|      56 | `commons-io:commons-io@2.18.0`                                       | https://gitbox.apache.org/repos/asf?p=commons-io.git                                     | resolve-plugins |
|      57 | `org.apache.bcel:bcel@6.10.0`                                        | https://gitbox.apache.org/repos/asf?p=commons-bcel.git                                   | resolve-plugins |
|      58 | `org.apache.commons:commons-collections4@4.4`                        | https://git-wip-us.apache.org/repos/asf?p=commons-collections.git                        | resolve-plugins |
|      59 | `commons-io:commons-io@2.16.1`                                       | https://gitbox.apache.org/repos/asf?p=commons-io.git                                     | resolve         |
|      60 | `commons-validator:commons-validator@1.9.0`                          | https://gitbox.apache.org/repos/asf/commons-validator                                    | resolve-plugins |
|      61 | `commons-digester:commons-digester@2.1`                              | http://svn.apache.org/viewvc/commons/proper/digester/tags/DIGESTER_2_1_RC2               | resolve-plugins |
|      62 | `commons-logging:commons-logging@1.3.2`                              | https://gitbox.apache.org/repos/asf/commons-logging                                      | resolve-plugins |
|      63 | `org.apache.maven:maven-core@3.1.0`                                  | https://git-wip-us.apache.org/repos/asf?p=maven.git/maven-core                           | resolve-plugins |
|      64 | `org.apache.maven:maven-settings@3.1.0`                              | https://git-wip-us.apache.org/repos/asf?p=maven.git/maven-settings                       | resolve-plugins |
|      65 | `org.apache.maven:maven-settings-builder@3.1.0`                      | https://git-wip-us.apache.org/repos/asf?p=maven.git/maven-settings-builder               | resolve-plugins |
|      66 | `org.apache.maven:maven-repository-metadata@3.1.0`                   | https://git-wip-us.apache.org/repos/asf?p=maven.git/maven-repository-metadata            | resolve-plugins |
|      67 | `org.apache.maven:maven-model-builder@3.1.0`                         | https://git-wip-us.apache.org/repos/asf?p=maven.git/maven-model-builder                  | resolve-plugins |
|      68 | `org.apache.maven:maven-aether-provider@3.1.0`                       | https://git-wip-us.apache.org/repos/asf?p=maven.git/maven-aether-provider                | resolve-plugins |
|      69 | `org.eclipse.aether:aether-spi@0.9.0.M2`                             | http://git.eclipse.org/c/aether/aether-core.git/tree/aether-spi/                         | resolve-plugins |
|      70 | `org.eclipse.aether:aether-impl@0.9.0.M2`                            | http://git.eclipse.org/c/aether/aether-core.git/tree/aether-impl/                        | resolve-plugins |
|      71 | `org.eclipse.aether:aether-api@0.9.0.M2`                             | http://git.eclipse.org/c/aether/aether-core.git/tree/aether-api/                         | resolve-plugins |
|      72 | `org.eclipse.aether:aether-util@0.9.0.M2`                            | http://git.eclipse.org/c/aether/aether-core.git/tree/aether-util/                        | resolve-plugins |
|      73 | `org.apache.maven:maven-artifact@3.1.0`                              | https://git-wip-us.apache.org/repos/asf?p=maven.git/maven-artifact                       | resolve-plugins |
|      74 | `org.apache.maven:maven-plugin-api@3.1.0`                            | https://git-wip-us.apache.org/repos/asf?p=maven.git/maven-plugin-api                     | resolve-plugins |
|      75 | `org.apache.maven:maven-model@2.2.1`                                 | http://svn.apache.org/viewvc/maven/maven-2/tags/maven-2.2.1/maven-model                  | resolve-plugins |
|      76 | `com.google.code.findbugs:jsr305@3.0.2`                              | https://code.google.com/p/jsr-305/                                                       | resolve         |
|      77 | `com.google.j2objc:j2objc-annotations@1.3`                           | http://svn.sonatype.org/spice/tags/oss-parent-7/j2objc-annotations                       | resolve-plugins |
|      78 | `net.sf.saxon:Saxon-HE@10.6`                                         | https://dev.saxonica.com/repos/archive/opensource/                                       | resolve-plugins |
|      79 | `org.apache.maven.shared:maven-shared-incremental@1.1`               | http://svn.apache.org/viewvc/maven/shared/tags/maven-shared-incremental-1.1              | resolve-plugins |
|      80 | `org.eclipse.jgit:org.eclipse.jgit@6.7.0.202309050840-r`             | https://git.eclipse.org/r/plugins/gitiles/jgit/jgit/org.eclipse.jgit                     | resolve-plugins |
|      81 | `org.apache.commons:commons-lang3@3.12.0`                            | https://gitbox.apache.org/repos/asf?p=commons-lang.git                                   | resolve-plugins |
|      82 | `org.ow2.asm:asm@9.4`                                                | https://gitlab.ow2.org/asm/asm/                                                          | resolve-plugins |
|      83 | `org.apache.maven.shared:maven-invoker@2.0.11`                       | http://svn.apache.org/viewvc/maven/shared/tags/maven-invoker-2.0.11                      | resolve-plugins |
|      84 | `com.martiansoftware:jsap@2.1`                                       | http://jsap.cvs.sourceforge.net/jsap/                                                    | resolve         |
|      85 | `org.apache.commons:commons-compress@1.27.0`                         | https://gitbox.apache.org/repos/asf?p=commons-compress.git                               | resolve         |
|      86 | `org.apache.commons:commons-lang3@3.16.0`                            | https://gitbox.apache.org/repos/asf?p=commons-lang.git                                   | resolve         |
|      87 | `org.kohsuke.metainf-services:metainf-services@1.11`                 | http://metainf-services.kohsuke.org/                                                     | resolve         |
</details>

### Fine grained information

:dolphin: For further information about software supply chain smells in your project, take a look at the following tables.

<details>
<summary>Source code links that could not be found(3)</summary>
    


|   index | package_name                                    | github_url                    | github_exists   | command         |
|--------:|:------------------------------------------------|:------------------------------|:----------------|:----------------|
|       1 | `org.sonatype.plexus:plexus-sec-dispatcher@1.3` | No_repo_info_found            |                 | resolve-plugins |
|       2 | `org.sonatype.plexus:plexus-cipher@1.4`         | No_repo_info_found            |                 | resolve-plugins |
|       3 | `org.iq80.snappy:snappy@0.4`                    | https://github.com/dain/snapy | False           | resolve-plugins |
</details>

<details>
<summary>List of packages with available source code repos but with inaccessible tags(55)</summary>
    


| package_name                                                                  | release_tag_exists   | tag_version                                 | github_url                                      | tag_related_info                        |   status_code_for_release_tag | command         |
|:------------------------------------------------------------------------------|:---------------------|:--------------------------------------------|:------------------------------------------------|:----------------------------------------|------------------------------:|:----------------|
| `org.apache.httpcomponents:httpclient@4.5.13`                                 | False                | `4.5.13`                                    | https://github.com/apache/httpcomponents-client | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.httpcomponents:httpcore@4.4.14`                                   | False                | `4.4.14`                                    | https://github.com/apache/httpcomponents-core   | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.maven.doxia:doxia-decoration-model@1.11.1`                        | False                | `1.11.1`                                    | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.maven.doxia:doxia-site-renderer@1.11.1`                           | False                | `1.11.1`                                    | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.maven.doxia:doxia-skin-model@1.11.1`                              | False                | `1.11.1`                                    | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.maven.doxia:doxia-integration-tools@1.11.1`                       | False                | `1.11.1`                                    | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.jetty:jetty-server@9.4.46.v20220331`                             | False                | `9.4.46.v20220331`                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.jetty:jetty-http@9.4.46.v20220331`                               | False                | `9.4.46.v20220331`                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.jetty:jetty-io@9.4.46.v20220331`                                 | False                | `9.4.46.v20220331`                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.jetty:jetty-servlet@9.4.46.v20220331`                            | False                | `9.4.46.v20220331`                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.jetty:jetty-security@9.4.46.v20220331`                           | False                | `9.4.46.v20220331`                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.jetty:jetty-util-ajax@9.4.46.v20220331`                          | False                | `9.4.46.v20220331`                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.jetty:jetty-webapp@9.4.46.v20220331`                             | False                | `9.4.46.v20220331`                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.jetty:jetty-xml@9.4.46.v20220331`                                | False                | `9.4.46.v20220331`                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.jetty:jetty-util@9.4.46.v20220331`                               | False                | `9.4.46.v20220331`                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.jdom:jdom2@2.0.6.1`                                                      | False                | `2.0.6.1`                                   | https://github.com/hunterhacker/jdom            | The given tag was not found in the repo |                           nan | resolve-plugins |
| `commons-codec:commons-codec@1.16.1`                                          | False                | `1.16.1`                                    | https://github.com/apache/commons-codec         | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.maven.doxia:doxia-site-renderer@2.0.0`                            | False                | `2.0.0`                                     | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.maven.doxia:doxia-site-model@2.0.0`                               | False                | `2.0.0`                                     | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.maven.doxia:doxia-skin-model@2.0.0`                               | False                | `2.0.0`                                     | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.sisu:org.eclipse.sisu.plexus@0.9.0.M3`                           | False                | `0.9.0.M3`                                  | https://github.com/eclipse/sisu.inject          | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.sisu:org.eclipse.sisu.inject@0.9.0.M3`                           | False                | `0.9.0.M3`                                  | https://github.com/eclipse/sisu.inject          | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.maven.doxia:doxia-integration-tools@2.0.0`                        | False                | `2.0.0`                                     | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.httpcomponents:httpclient@4.5.14`                                 | False                | `4.5.14`                                    | https://github.com/apache/httpcomponents-client | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.httpcomponents:httpcore@4.4.16`                                   | False                | `4.4.16`                                    | https://github.com/apache/httpcomponents-core   | The given tag was not found in the repo |                           nan | resolve-plugins |
| `commons-codec:commons-codec@1.17.1`                                          | False                | `1.17.1`                                    | https://github.com/apache/commons-codec         | The given tag was not found in the repo |                           nan | resolve         |
| `org.eclipse.sisu:org.eclipse.sisu.plexus@0.9.0.M2`                           | False                | `0.9.0.M2`                                  | https://github.com/eclipse/sisu.plexus          | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.sisu:org.eclipse.sisu.inject@0.9.0.M2`                           | False                | `0.9.0.M2`                                  | https://github.com/eclipse/sisu.inject          | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.google.guava:guava@31.0.1-jre`                                           | False                | `31.0.1-jre`                                | https://github.com/google/guava                 | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.google.guava:listenablefuture@9999.0-empty-to-avoid-conflict-with-guava` | False                | `9999.0-empty-to-avoid-conflict-with-guava` | https://github.com/google/guava                 | The given tag was not found in the repo |                           nan | resolve         |
| `org.javassist:javassist@3.28.0-GA`                                           | False                | `3.28.0-GA`                                 | https://github.com/jboss-javassist/javassist    | The given tag was not found in the repo |                           nan | resolve-plugins |
| `javax.activation:javax.activation-api@1.2.0`                                 | False                | `1.2.0`                                     | https://github.com/javaee/activation            | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.apache.maven.plugins:maven-compiler-plugin@3.13.0`                       | False                | `3.13.0`                                    | https://github.com/apache/maven-compiler-plugin | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.diffplug.spotless:spotless-maven-plugin@2.43.0`                          | False                | `2.43.0`                                    | https://github.com/diffplug/spotless            | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.diffplug.spotless:spotless-lib@2.45.0`                                   | False                | `2.45.0`                                    | https://github.com/diffplug/spotless            | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.diffplug.spotless:spotless-lib-extra@2.45.0`                             | False                | `2.45.0`                                    | https://github.com/diffplug/spotless            | The given tag was not found in the repo |                           nan | resolve-plugins |
| `dev.equo.ide:solstice@1.7.5`                                                 | False                | `1.7.5`                                     | https://github.com/equodev/equo-ide             | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.eclipse.platform:org.eclipse.osgi@3.18.300`                              | False                | `3.18.300`                                  | https://github.com/eclipse-equinox/equinox      | The given tag was not found in the repo |                           nan | resolve-plugins |
| `org.jetbrains:annotations@13.0`                                              | False                | `13.0`                                      | https://github.com/jetbrains/intellij-community | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.diffplug.durian:durian-core@1.2.0`                                       | False                | `1.2.0`                                     | https://github.com/diffplug/durian              | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.diffplug.durian:durian-io@1.2.0`                                         | False                | `1.2.0`                                     | https://github.com/diffplug/durian              | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.diffplug.durian:durian-collect@1.2.0`                                    | False                | `1.2.0`                                     | https://github.com/diffplug/durian              | The given tag was not found in the repo |                           nan | resolve-plugins |
| `commons-codec:commons-codec@1.16.0`                                          | False                | `1.16.0`                                    | https://github.com/apache/commons-codec         | The given tag was not found in the repo |                           nan | resolve-plugins |
| `se.kth.castor:depclean-maven-plugin@2.0.6`                                   | False                | `2.0.6`                                     | https://github.com/castor-software/depclean     | The given tag was not found in the repo |                           nan | resolve-plugins |
| `se.kth.castor:depclean-core@2.0.6`                                           | False                | `2.0.6`                                     | https://github.com/castor-software/depclean     | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.google.guava:guava@31.1-jre`                                             | False                | `31.1-jre`                                  | https://github.com/google/guava                 | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.google.code.gson:gson@2.10`                                              | False                | `2.10`                                      | https://github.com/google/gson                  | The given tag was not found in the repo |                           nan | resolve-plugins |
| `com.google.guava:guava@33.2.1-jre`                                           | False                | `33.2.1-jre`                                | https://github.com/google/guava                 | The given tag was not found in the repo |                           nan | resolve         |
| `com.mysema.querydsl:querydsl-core@3.7.4`                                     | False                | `3.7.4`                                     | https://github.com/querydsl/querydsl            | The given tag was not found in the repo |                           nan | resolve         |
| `org.assertj:assertj-core@3.26.3`                                             | False                | `3.26.3`                                    | https://github.com/assertj/assertj              | The given tag was not found in the repo |                           nan | resolve         |
| `org.eclipse.jdt:ecj@3.38.0`                                                  | False                | `3.38.0`                                    | https://github.com/eclipse-jdt/eclipse.jdt.core | The given tag was not found in the repo |                           nan | resolve         |
| `org.eclipse.jdt:org.eclipse.jdt.core@3.38.0`                                 | False                | `3.38.0`                                    | https://github.com/eclipse-jdt/eclipse.jdt.core | The given tag was not found in the repo |                           nan | resolve         |
| `org.junit.platform:junit-platform-commons@1.10.3`                            | False                | `1.10.3`                                    | https://github.com/junit-team/junit5            | The given tag was not found in the repo |                           nan | resolve         |
| `org.junit.platform:junit-platform-engine@1.10.3`                             | False                | `1.10.3`                                    | https://github.com/junit-team/junit5            | The given tag was not found in the repo |                           nan | resolve         |
| `org.junit.platform:junit-platform-launcher@1.10.3`                           | False                | `1.10.3`                                    | https://github.com/junit-team/junit5            | The given tag was not found in the repo |                           nan | resolve         |
</details>

The package manager (maven) does not support checking for deprecated packages.

<details>
<summary>List of packages without code signature(14)</summary>
    


| package_name                                              | command         |
|:----------------------------------------------------------|:----------------|
| `javax.inject:javax.inject@1`                             | resolve         |
| `aopalliance:aopalliance@1.0`                             | resolve-plugins |
| `org.codehaus.plexus:plexus-i18n@1.0-beta-10`             | resolve-plugins |
| `com.google.collections:google-collections@1.0`           | resolve-plugins |
| `commons-beanutils:commons-beanutils@1.7.0`               | resolve-plugins |
| `commons-digester:commons-digester@1.8`                   | resolve-plugins |
| `commons-chain:commons-chain@1.1`                         | resolve-plugins |
| `dom4j:dom4j@1.1`                                         | resolve-plugins |
| `oro:oro@2.0.8`                                           | resolve-plugins |
| `org.apache.maven.scm:maven-scm-providers-standard@2.1.0` | resolve-plugins |
| `com.google.code.findbugs:jsr305@2.0.0`                   | resolve-plugins |
| `commons-lang:commons-lang@1.0`                           | resolve-plugins |
| `com.martiansoftware:jsap@2.1`                            | resolve         |
| `javax.validation:validation-api@2.0.1.Final`             | resolve         |
</details>

All packages have valid code signature.

The package manager (maven) does not support checking for provenance.

The package manager (maven) does not support checking for aliased packages.

### Call to Action:

<details>
<summary>👻What do I do now? </summary>


For packages **without source code & accessible release tags**:

- **Why?** Missing or inaccessible source code makes it impossible to audit the package for security vulnerabilities or malicious code.

1. Pull Request to the maintainer of dependency, requesting correct repository metadata and proper tagging. 


For **deprecated** packages:

- **Why?** Deprecated packages may contain known security issues and are no longer maintained, putting your project at risk.

1. Confirm the maintainer's deprecation intention 
2. Check for not deprecated versions

For packages **without code signature**:

- **Why?** Code signatures help verify the authenticity and integrity of the package, ensuring it hasn't been tampered with.

1. Open an issue in the dependency's repository to request the inclusion of code signature in the CI/CD pipeline. 


For packages **with invalid code signature**:

- **Why?** Invalid signatures could indicate tampering or compromised build processes.

1. It's recommended to verify the code signature and contact the maintainer to fix the issue.

For packages **without provenance**:

- **Why?** Without provenance, there's no way to verify that the package was built from the claimed source code, making supply chain attacks possible.

1. Open an issue in the dependency's repository to request the inclusion of provenance and build attestation in the CI/CD pipeline.

For packages that are **aliased**:

- **Why?** Aliased packages may hide malicious dependencies under seemingly legitimate names.

1. Check the aliased package and its repository to verify the alias is not malicious.
</details>


---

Report created by [dirty-waters](https://github.com/chains-project/dirty-waters/).

Report created on 2025-03-11 14:38:05
- Tool version: 9e0f952b
- Project Name: INRIA/spoon
- Project Version: v11.1.0
