
# Software Supply Chain Report of INRIA/spoon - v11.1.0

## Enabled Checks
The following checks were specifically requested:

- Source Code
- Release Tags
- Deprecated
- Forks
- Provenance
- Code Signature

---


<details>
    <summary>How to read the results :book: </summary>
    
 Dirty-waters has analyzed your project dependencies and found different categories for each of them:

    
 - ⚠️⚠️⚠️ : high severity 

    
 - ⚠️⚠️: medium severity 

    
 - ⚠️: low severity 

</details>
        

 ### Total packages in the supply chain: 420


:heavy_exclamation_mark: Packages with no source code URL (⚠️⚠️⚠️): 2

:no_entry: Packages with repo URL that is 404 (⚠️⚠️⚠️): 2

:wrench: Packages with inaccessible GitHub tag (⚠️⚠️): 56

:cactus: Packages that are forks (⚠️⚠️): 3

:lock: Packages without code signature (⚠️⚠️): 14


<details>
    <summary>Other info:</summary>
    
- Source code repo is not hosted on GitHub:  94

    This could be due to the package being hosted on a different platform or the package not having a source code repo.

</details>
                            
                            
### Fine grained information

:dolphin: For further information about software supply chain smells in your project, take a look at the following tables.

<details>
<summary>Source code links that could not be found(4)</summary>
    


|   index | package_name                                  | github_url                           | github_exists   | command         |
|--------:|:----------------------------------------------|:-------------------------------------|:----------------|:----------------|
|       1 | org.sonatype.plexus:plexus-sec-dispatcher@1.3 | No_repo_info_found                   |                 | resolve-plugins |
|       2 | org.sonatype.plexus:plexus-cipher@1.4         | No_repo_info_found                   |                 | resolve-plugins |
|       3 | org.iq80.snappy:snappy@0.4                    | https://github.com/dain/snapy        | False           | resolve-plugins |
|       4 | junit:junit@4.13.2                            | https://github.com/junit-team/junit4 | False           | resolve-plugins |
</details>

<details>
<summary>List of packages with available source code repos but with inaccessible tags(56)</summary>
    


| package_name                                                                | release_tag_exists   | tag_version                               | github_url                                      | tag_related_info                        | status_code_for_release_tag   | command         |
|:----------------------------------------------------------------------------|:---------------------|:------------------------------------------|:------------------------------------------------|:----------------------------------------|:------------------------------|:----------------|
| org.apache.httpcomponents:httpclient@4.5.13                                 | False                | 4.5.13                                    | https://github.com/apache/httpcomponents-client | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.httpcomponents:httpcore@4.4.14                                   | False                | 4.4.14                                    | https://github.com/apache/httpcomponents-core   | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.maven.doxia:doxia-decoration-model@1.11.1                        | False                | 1.11.1                                    | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.maven.doxia:doxia-site-renderer@1.11.1                           | False                | 1.11.1                                    | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.maven.doxia:doxia-skin-model@1.11.1                              | False                | 1.11.1                                    | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.maven.doxia:doxia-integration-tools@1.11.1                       | False                | 1.11.1                                    | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.jetty:jetty-server@9.4.46.v20220331                             | False                | 9.4.46.v20220331                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.jetty:jetty-http@9.4.46.v20220331                               | False                | 9.4.46.v20220331                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.jetty:jetty-io@9.4.46.v20220331                                 | False                | 9.4.46.v20220331                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.jetty:jetty-servlet@9.4.46.v20220331                            | False                | 9.4.46.v20220331                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.jetty:jetty-security@9.4.46.v20220331                           | False                | 9.4.46.v20220331                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.jetty:jetty-util-ajax@9.4.46.v20220331                          | False                | 9.4.46.v20220331                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.jetty:jetty-webapp@9.4.46.v20220331                             | False                | 9.4.46.v20220331                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.jetty:jetty-xml@9.4.46.v20220331                                | False                | 9.4.46.v20220331                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.jetty:jetty-util@9.4.46.v20220331                               | False                | 9.4.46.v20220331                          | https://github.com/eclipse/jetty.project        | The given tag was not found in the repo |                               | resolve-plugins |
| org.jdom:jdom2@2.0.6.1                                                      | False                | 2.0.6.1                                   | https://github.com/hunterhacker/jdom            | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.maven.resolver:maven-resolver-api@1.9.18                         | False                | 1.9.18                                    | https://github.com/apache/maven-resolver        | The given tag was not found in the repo |                               | resolve-plugins |
| commons-codec:commons-codec@1.16.1                                          | False                | 1.16.1                                    | https://github.com/apache/commons-codec         | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.maven.doxia:doxia-site-renderer@2.0.0                            | False                | 2.0.0                                     | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.maven.doxia:doxia-site-model@2.0.0                               | False                | 2.0.0                                     | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.maven.doxia:doxia-skin-model@2.0.0                               | False                | 2.0.0                                     | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.sisu:org.eclipse.sisu.plexus@0.9.0.M3                           | False                | 0.9.0.M3                                  | https://github.com/eclipse/sisu.inject          | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.sisu:org.eclipse.sisu.inject@0.9.0.M3                           | False                | 0.9.0.M3                                  | https://github.com/eclipse/sisu.inject          | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.maven.doxia:doxia-integration-tools@2.0.0                        | False                | 2.0.0                                     | https://github.com/apache/maven-doxia-sitetools | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.httpcomponents:httpclient@4.5.14                                 | False                | 4.5.14                                    | https://github.com/apache/httpcomponents-client | The given tag was not found in the repo |                               | resolve-plugins |
| org.apache.httpcomponents:httpcore@4.4.16                                   | False                | 4.4.16                                    | https://github.com/apache/httpcomponents-core   | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.sisu:org.eclipse.sisu.plexus@0.9.0.M2                           | False                | 0.9.0.M2                                  | https://github.com/eclipse/sisu.plexus          | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.sisu:org.eclipse.sisu.inject@0.9.0.M2                           | False                | 0.9.0.M2                                  | https://github.com/eclipse/sisu.inject          | The given tag was not found in the repo |                               | resolve-plugins |
| com.google.guava:guava@31.0.1-jre                                           | False                | 31.0.1-jre                                | https://github.com/google/guava                 | The given tag was not found in the repo |                               | resolve-plugins |
| com.google.guava:listenablefuture@9999.0-empty-to-avoid-conflict-with-guava | False                | 9999.0-empty-to-avoid-conflict-with-guava | https://github.com/google/guava                 | The given tag was not found in the repo |                               | resolve         |
| org.javassist:javassist@3.28.0-GA                                           | False                | 3.28.0-GA                                 | https://github.com/jboss-javassist/javassist    | The given tag was not found in the repo |                               | resolve-plugins |
| javax.activation:javax.activation-api@1.2.0                                 | False                | 1.2.0                                     | https://github.com/javaee/activation            | The given tag was not found in the repo |                               | resolve-plugins |
| com.diffplug.spotless:spotless-maven-plugin@2.43.0                          | False                | 2.43.0                                    | https://github.com/diffplug/spotless            | The given tag was not found in the repo |                               | resolve-plugins |
| com.diffplug.spotless:spotless-lib@2.45.0                                   | False                | 2.45.0                                    | https://github.com/diffplug/spotless            | The given tag was not found in the repo |                               | resolve-plugins |
| com.diffplug.spotless:spotless-lib-extra@2.45.0                             | False                | 2.45.0                                    | https://github.com/diffplug/spotless            | The given tag was not found in the repo |                               | resolve-plugins |
| dev.equo.ide:solstice@1.7.5                                                 | False                | 1.7.5                                     | https://github.com/equodev/equo-ide             | The given tag was not found in the repo |                               | resolve-plugins |
| org.eclipse.platform:org.eclipse.osgi@3.18.300                              | False                | 3.18.300                                  | https://github.com/eclipse-equinox/equinox      | The given tag was not found in the repo |                               | resolve-plugins |
| org.jetbrains:annotations@13.0                                              | False                | 13.0                                      | https://github.com/jetbrains/intellij-community | The given tag was not found in the repo |                               | resolve-plugins |
| com.diffplug.durian:durian-core@1.2.0                                       | False                | 1.2.0                                     | https://github.com/diffplug/durian              | The given tag was not found in the repo |                               | resolve-plugins |
| com.diffplug.durian:durian-io@1.2.0                                         | False                | 1.2.0                                     | https://github.com/diffplug/durian              | The given tag was not found in the repo |                               | resolve-plugins |
| com.diffplug.durian:durian-collect@1.2.0                                    | False                | 1.2.0                                     | https://github.com/diffplug/durian              | The given tag was not found in the repo |                               | resolve-plugins |
| commons-codec:commons-codec@1.16.0                                          | False                | 1.16.0                                    | https://github.com/apache/commons-codec         | The given tag was not found in the repo |                               | resolve-plugins |
| se.kth.castor:depclean-maven-plugin@2.0.6                                   | False                | 2.0.6                                     | https://github.com/castor-software/depclean     | The given tag was not found in the repo |                               | resolve-plugins |
| se.kth.castor:depclean-core@2.0.6                                           | False                | 2.0.6                                     | https://github.com/castor-software/depclean     | The given tag was not found in the repo |                               | resolve-plugins |
| com.google.guava:guava@31.1-jre                                             | False                | 31.1-jre                                  | https://github.com/google/guava                 | The given tag was not found in the repo |                               | resolve-plugins |
| com.google.code.gson:gson@2.10                                              | False                | 2.10                                      | https://github.com/google/gson                  | The given tag was not found in the repo |                               | resolve-plugins |
| commons-codec:commons-codec@1.17.0                                          | False                | 1.17.0                                    | https://github.com/apache/commons-codec         | The given tag was not found in the repo |                               | resolve-plugins |
| com.google.guava:guava@33.2.1-jre                                           | False                | 33.2.1-jre                                | https://github.com/google/guava                 | The given tag was not found in the repo |                               | resolve         |
| com.mysema.querydsl:querydsl-core@3.7.4                                     | False                | 3.7.4                                     | https://github.com/querydsl/querydsl            | The given tag was not found in the repo |                               | resolve         |
| commons-codec:commons-codec@1.17.1                                          | False                | 1.17.1                                    | https://github.com/apache/commons-codec         | The given tag was not found in the repo |                               | resolve         |
| org.assertj:assertj-core@3.26.3                                             | False                | 3.26.3                                    | https://github.com/assertj/assertj              | The given tag was not found in the repo |                               | resolve         |
| org.eclipse.jdt:ecj@3.38.0                                                  | False                | 3.38.0                                    | https://github.com/eclipse-jdt/eclipse.jdt.core | The given tag was not found in the repo |                               | resolve         |
| org.eclipse.jdt:org.eclipse.jdt.core@3.38.0                                 | False                | 3.38.0                                    | https://github.com/eclipse-jdt/eclipse.jdt.core | The given tag was not found in the repo |                               | resolve         |
| org.junit.platform:junit-platform-commons@1.10.3                            | False                | 1.10.3                                    | https://github.com/junit-team/junit5            | The given tag was not found in the repo |                               | resolve         |
| org.junit.platform:junit-platform-engine@1.10.3                             | False                | 1.10.3                                    | https://github.com/junit-team/junit5            | The given tag was not found in the repo |                               | resolve         |
| org.junit.platform:junit-platform-launcher@1.10.3                           | False                | 1.10.3                                    | https://github.com/junit-team/junit5            | The given tag was not found in the repo |                               | resolve         |
</details>

The package manager (maven) does not support checking for deprecated packages.

<details>
<summary>List of packages from fork(3)</summary>
    


| package_name                                       | is_fork   | parent_repo_link                                       | command         |
|:---------------------------------------------------|:----------|:-------------------------------------------------------|:----------------|
| com.github.cliftonlabs:json-simple@3.0.2           | True      | https://github.com/fangyidong/json-simple              | resolve-plugins |
| org.jgrapht:jgrapht-core@1.5.1                     | True      | https://github.com/lingeringsocket/jgrapht             | resolve-plugins |
| org.whitesource:maven-dependency-tree-parser@1.0.6 | True      | https://github.com/adutra/maven-dependency-tree-parser | resolve-plugins |
</details>

<details>
<summary>List of packages without code signature(14)</summary>
    


| package_name                                            | signature_present   | command         |
|:--------------------------------------------------------|:--------------------|:----------------|
| javax.inject:javax.inject@1                             | False               | resolve         |
| aopalliance:aopalliance@1.0                             | False               | resolve-plugins |
| org.codehaus.plexus:plexus-i18n@1.0-beta-10             | False               | resolve-plugins |
| com.google.collections:google-collections@1.0           | False               | resolve-plugins |
| commons-beanutils:commons-beanutils@1.7.0               | False               | resolve-plugins |
| commons-digester:commons-digester@1.8                   | False               | resolve-plugins |
| commons-chain:commons-chain@1.1                         | False               | resolve-plugins |
| dom4j:dom4j@1.1                                         | False               | resolve-plugins |
| oro:oro@2.0.8                                           | False               | resolve-plugins |
| org.apache.maven.scm:maven-scm-providers-standard@2.1.0 | False               | resolve-plugins |
| com.google.code.findbugs:jsr305@2.0.0                   | False               | resolve-plugins |
| commons-lang:commons-lang@1.0                           | False               | resolve-plugins |
| com.martiansoftware:jsap@2.1                            | False               | resolve         |
| javax.validation:validation-api@2.0.1.Final             | False               | resolve         |
</details>

All packages have valid code signature.

The package manager (maven) does not support checking for provenance.

### Call to Action:

                      
<details>
    <summary>👻What do I do now? </summary>
        For packages without source code & accessible release tags:  

        Pull Request to the maintainer of dependency, requesting correct repository metadata and proper tagging. 

        
For deprecated packages:

        1. Confirm the maintainer’s deprecation intention 
        2. Check for not deprecated versions
        
For packages without provenance:

        Open an issue in the dependency’s repository to request the inclusion of provenance and build attestation in the CI/CD pipeline. 
        
For packages that are forks

        Inspect the package and its GitHub repository to verify the fork is not malicious. 

        
For packages without code signature:

        Open an issue in the dependency’s repository to request the inclusion of code signature in the CI/CD pipeline. 

        
For packages with invalid code signature:

        It's recommended to verify the code signature and contact the maintainer to fix the issue. 

</details>



---

Report created by [dirty-waters](https://github.com/chains-project/dirty-waters/).

Report created on 2025-02-20 14:57:10
- Tool version: 3712a094
- Project Name: INRIA/spoon
- Project Version: v11.1.0
