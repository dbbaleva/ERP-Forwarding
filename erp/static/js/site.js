// configure jquery validation
if ($.validator) {
    $.validator.setDefaults({
        ignore: "input[type=\"hidden\"], .tt-hint, .ignore",
        onkeyup: false
    });

}

// Avoid `console` errors in browsers that lack a console.
(function () {
    var method;
    var noop = function () {
    };
    var methods = [
        "assert", "clear", "count", "debug", "dir", "dirxml", "error",
        "exception", "group", "groupCollapsed", "groupEnd", "info", "log",
        "markTimeline", "profile", "profileEnd", "table", "time", "timeEnd",
        "timeStamp", "trace", "warn"
    ];
    var length = methods.length;
    var console = (window.console = window.console || {});
    while (length--) {
        method = methods[length];
        // Only stub undefined methods.
        if (!console[method]) {
            console[method] = noop;
        }
    }
    Number.prototype.toFormattedString = function (number) {
        if (!number) number = 2;
        return this >= 0
            ? this.toFixed(number).replace(/\d(?=(\d{3})+\.)/g, "$&,")
            : "(" + Math.abs(this).toFixed(number).replace(/\d(?=(\d{3})+\.)/g, "$&,") + ")";

    };
    Array.prototype.remove = function (el) {
        var i = this.indexOf(el);
        if (i !== -1) {
            this.splice(i, 1);
        }
    };
}());

(function ($) {
    // toggle function
    $.fn.clickToggle = function (f1, f2) {
        return this.each(function () {
            var clicked = false;
            $(this).bind("click", function () {
                if (clicked) {
                    clicked = false;
                    return f2.apply(this, arguments);
                }

                clicked = true;
                return f1.apply(this, arguments);
            });
        });

    }

    //*******************************************
    /*	AUTOCOMPLETE
     /********************************************/

    $.fn.autoComplete = function () {
        $.each(this, function () {
            var $self = $(this),
                cell = $self.closest(".edit-cell"),
                valueKey = "Id",
                displayKey = "Name",
                model = $self.data("model"),
                url = $self.data("url"),
                init = $self.data("init");

            if ($self.find(".twitter-typeahead").length > 0) {
                return;
            }

            if (cell.length > 0) {
                $(this).css("width", cell.width());
            }

            if (init) {
                if (window[init])
                    window[init]($self);
            } else {
                var engine = new Bloodhound({
                    datumTokenizer: Bloodhound.tokenizers.obj.whitespace("Name"),
                    queryTokenizer: Bloodhound.tokenizers.whitespace,
                    remote: {
                        url: url,
                        wildcard: "%QUERY",
                        ajax: {
                            headers: {
                                Accept: "application/json; charset=utf-8",
                                "Content-Type": "text/plain; charset=utf-8"
                            }
                        },
                        filter: function (json) {
                            if (json["@odata.context"]) {
                                return $.map(json.value, function (data) {
                                    return {
                                        Id: data.Id,
                                        Name: data.Name
                                    }
                                });
                            }
                            return json;
                        }
                    }
                });

                $self.find(".typeahead").typeahead({
                    hint: true,
                    highlight: true,
                    minLength: 1
                }, {
                    displayKey: displayKey,
                    source: engine
                }).on(
                    "typeahead:selected",
                    function (e, d) {
                        var id = "";
                        if (model != null) {
                            id = "#" + model.replace(".", "_");
                            $self.find(id).val(d[valueKey]);
                        }
                        // raise event
                        if (id !== "") {
                            $(id).trigger("autocomplete:selected",
                                [$self, {Id: d[valueKey], Name: d[displayKey]}]);
                        }
                    }
                );
            }
        });
    };

    $.fn.simulateLoading = function () {
        $(this).append($("<div/>", {
            "class": "loading",
            "text": "Loading&hellip;"
        }));
    };

    $.fn.autoGrowInput = function (o) {

        o = $.extend({
            maxWidth: 1000,
            minWidth: 0,
            comfortZone: 50
        }, o);

        this.filter("input:text").each(function () {

            var minWidth = o.minWidth || $(this).width(),
                val = "",
                input = $(this),
                testSubject = $("<tester/>").css({
                    position: "absolute",
                    top: -9999,
                    left: -9999,
                    width: 'auto',
                    fontSize: input.css("fontSize"),
                    fontFamily: input.css("fontFamily"),
                    fontWeight: input.css("fontWeight"),
                    letterSpacing: input.css("letterSpacing"),
                    whiteSpace: "nowrap"
                }),

                check = function () {

                    if (val === (val = input.val())) {
                        return;
                    }

                    // Enter new content into testSubject
                    var escaped = val.replace(/&/g, "&amp;").replace(/\s/g, "&nbsp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                    testSubject.html(escaped);

                    // Calculate new width + whether to change
                    var testerWidth = testSubject.width(),
                        newWidth = (testerWidth + o.comfortZone) >= minWidth ? testerWidth + o.comfortZone : minWidth,
                        currentWidth = input.width(),
                        isValidWidthChange = (newWidth < currentWidth && newWidth >= minWidth)
                            || (newWidth > minWidth && newWidth < o.maxWidth);

                    // Animate width
                    if (isValidWidthChange) {
                        input.width(newWidth);
                    }

                };

            testSubject.insertAfter(input);

            $(this).bind("keyup keydown blur update", check);

        });

        return this;
    };

    $.fn.attachGridPlugins = function () {
        var context = $(document),
            form = $(this).find("#form-grid"),
            searchBox = $("div.searchbox"),

            // auto indent search text box depending on tag width
            indent = function() {
                searchBox.find("input").css({
                    textIndent: searchBox.find(".tags").width()
                });
            },

            // create a search tag from label
            create_search_tag = function(s) {
                var text= $(s).data("tag"),
                    values = text.split(":"),
                    tag_type = values[0].toLowerCase(),
                    tag_value = values[1].trim(),
                    tag = $("<span>", {
                        "class": "tag label",
                        "data-tag-type": tag_type,
                        "data-tag-value": tag_value
                    }).text(text).append(
                        $("<span>", {
                            "data-role": "remove"
                        })
                    );

                return tag;
            },

            remove_search_tag = function(tag) {
                tag.remove();
                indent();
                update_search_params();
                form.submit();
            },

            // gets the default css for the search tag
            get_tag_css = function(s) {
                var css_list = $(s).attr("class").split(" ");
                for (var i=0; i<css_list.length; i++) {
                    if (/^label/.test(css_list[i])) {
                        return css_list[i];
                    }
                }
                return "label-info";
            },

            // updates the search parameters as per tag and search input
            update_search_params = function() {
                var tags = searchBox.find(".tag"),
                    params = form.find("#search-params");

                params.html(null);

                tags.each(function() {
                    var i = $("<input>",{
                       "type": "hidden",
                        "name": $(this).data("tagType"),
                        "value": $(this).data("tagValue")
                    });

                    params.append(i);
                });
            };

        // add some css on search box when focused
        context.on(
            "click",
            "div.searchbox",
            function () {
                $(this).addClass("focus");
                $(this).find("input").focus();
            }
        );

        // remove css from search box when not focused
        context.on(
            "focusout",
            "div.searchbox",
            function () {
                $(this).removeClass("focus");
            }
        );

        // remove search box tag when clicked on remove button
        context.on(
            "click",
            "div.searchbox [data-role=remove]",
            function() {
                remove_search_tag($(this).closest(".tag"));
            }
        );

        context.on(
            "click",
            ".inbox-left-menu .tags li a[data-remove-tag]",
            function(e) {
                e.preventDefault();
                var tags = searchBox.find(".tags"),
                    type = $(this).data("removeTag").toLowerCase(),
                    target = tags.find("[data-tag-type=" + type + "]");

                remove_search_tag(target);
            }
        );

        // adds a label as search box tag
        context.on(
            "click",
            ".inbox-left-menu .tags li a[data-tag]",
            function(e) {
                e.preventDefault();
                var tag = create_search_tag(this),
                    type = tag.data("tagType"),
                    tags = searchBox.find(".tags"),
                    target = tags.find("[data-tag-type=" + type + "]"),
                    css = get_tag_css($(this).closest("li").find("i"));

                tag.addClass(css);

                if (target.length > 0) {
                    target.remove();
                }

                tags.append(tag);

                indent();
                update_search_params();
                form.submit();
            }
        );

        // refresh grid
        context.on(
            "click",
            "#refresh",
            function () {
                form.submit();
            }
        );

        // inbox responsive left nav
        context.on(
            "click",
            ".inbox-nav-toggle",
            function () {
                $(".inbox-left-menu").toggleClass("active");
            }
        );

        // handle navigation/paging
        context.on(
            "click",
            ".pager li > a",
            function (e) {
                e.preventDefault();

                if ($(this).hasClass("disabled")) {
                    return;
                }

                var i = $(this).find("i");
                var step = i.hasClass("fa-angle-left") ? -1 :
                    i.hasClass("fa-angle-right") ? 1 : 0;
                var pager = $(this).closest(".pager");
                var page = parseInt(pager.data("currentpage")) + step;
                var url = form.attr("action");

                $(".messages").simulateLoading();

                form.ajaxSubmit({
                    type: "POST",
                    url: url,
                    data: {
                        page: page
                    },
                    success: function (result) {
                        $(".inbox-content").html(result);
                    }
                });
            }
        );

        // handle grid row selection
        context.on(
            "change",
            ".message-table .fancy-checkbox",
            function (event) {
                event.stopPropagation();
                if ($(this).find(":checkbox").is(":checked")) {
                    $(this).parents("tr").addClass("highlighted");
                } else {
                    $(this).parents("tr").removeClass("highlighted");
                }

                // show/hide top menu
                if ($(".message-table tr.highlighted").length > 0) {
                    $(".top-menu .context-menu").removeClass("hide");
                    $(".top-menu .toggle-menu").addClass("hide");
                } else {
                    $(".top-menu .context-menu").addClass("hide");
                    $(".top-menu .toggle-menu").removeClass("hide");
                }

                // toggle fancy-checkbox-all
                $(".top-menu .fancy-checkbox-all").find(":checkbox").prop("checked",
                    $(".message-table tr:not(.highlighted)").length === 0);
            }
        );


        // inbox check all message
        context.on(
            "change",
            ".top-menu .fancy-checkbox-all",
            function () {
                var table_rows = $(".message-table tr:not(.empty-row)");
                if (table_rows.length == 0) {
                    return;
                }
                if ($(this).find(":checkbox").is(":checked")) {
                    table_rows.find(".fancy-checkbox>:checkbox").prop("checked", true);
                    table_rows.addClass("highlighted");
                    $(".top-menu .context-menu").removeClass("hide");
                    $(".top-menu .toggle-menu").addClass("hide");
                } else {
                    table_rows.find(".fancy-checkbox>:checkbox").prop("checked", false);
                    table_rows.removeClass("highlighted");
                    $(".top-menu .context-menu").addClass("hide");
                    $(".top-menu .toggle-menu").removeClass("hide");
                }
            }
        );

        // default implementation on grid row status-update
        context.on(
            "click",
            ".status-update",
            function (e) {
                var status = $(this).data("status");
                var dropdown = $(this).closest(".dropdown-menu");
                var parent = $(this).closest("[data-url]");
                var url = parent.data("url");
                var selection = $(".message-table tr.highlighted");

                e.preventDefault();

                if (dropdown.length > 0) {
                    parent.closest(".open").removeClass("open");
                }

                if (selection.length > 0 && confirm("This will update " + selection.length + " record(s) to " +
                        status.toUpperCase() + " status.\n Confirm action?")) {

                    var data = {
                        status: status
                    };

                    $.each(selection, function (i, o) {
                        data['id-' + i] = $(this).data('uid');
                    });

                    $(".messages").simulateLoading();

                    form.ajaxSubmit({
                        type: "POST",
                        url: url,
                        data: data,
                        success: function (result) {
                            $(".inbox-content").html(result);
                        }
                    });
                }
            }
        );
    };

    $.fn.serializeObject = function (cleanRE) {
        var o = {};
        var a = this.serializeArray();
        $.each(a, function () {
            var name = this.name;
            if (cleanRE) {
                name = cleanRE(name);
            }
            if (o[name] !== undefined) {
                if (!o[name].push) {
                    o[name] = [o[name]];
                }
                o[name].push(this.value || '');
            } else {
                o[name] = this.value || '';
            }
        });
        return o;
    };

    $.fn.attachFormPlugins = function () {
        var $input, $options;
        //*******************************************
        //*	MULTISELECT
        //********************************************/
        if ($.fn.multiselect) {
            $(".multiselect").multiselect({
                inheritClass: true
            });
        }

        //*******************************************
        //*	SELECT2
        //********************************************/
        if ($.fn.select2) {
            $input = $(".select2");
            $options = $input.data("options") || {};
            $options["width"] = "100%";
            $input.select2($options);
        }

        //*******************************************
        //*	DATETIME PICKER
        //********************************************/
        if ($.fn.datetimepicker) {

            getOptions = function(s) {
                var data = s.data();
                var options = {};
                for (var opt in data) {
                    if (/^options/.test(opt)) {
                        var name = opt.replace(/^options/,"").toLowerCase();
                        options[name] = data[opt];
                    }
                }
                return options;
            };

            $input = $(".input-daterange");
            if ($input.length > 0) {
                $input.find("input").datetimepicker(getOptions($input));
            }

            $input = $(".datetimepicker");
            if ($input.length > 0) {
                $input.datetimepicker(getOptions($input));
            }
        }

        //*******************************************
        //*	SUMMERNOTE
        //********************************************/
        if ($.fn.summernote) {
            $(".summernote").summernote({
                toolbar: [
                    //[groupname, [button list]]
                    ["style", ["bold", "italic", "underline", "clear"]],
                    ["font", ["strikethrough", "superscript", "subscript"]],
                    ["fontsize", ["fontname", "fontsize"]],
                    ["color", ["color"]],
                    ["para", ["ul", "ol", "paragraph"]],
                    ["height", ["height"]]
                ],
                height: 300,
                onBlur: function () {
                    var input = "#" + $(this).data("input");
                    $(input).val($(this).code());
                }
            });
        }

        //*******************************************
        //*	TWITTER TYPEAHEAD
        //********************************************/
        if ($.fn.autoComplete) {
            $(".autocomplete").autoComplete();
        }

        return this
    };

    $.fn.attachFormEvents = function () {
        if ($(this).length == 0) {
            return;
        }
        //*******************************************
        //* TOP MENU
        //*******************************************/
        $(document).on(
            "click",
            ".top-menu .cancel > a",
            function (e) {
                if (!confirm("You have chosen to cancel data entry. Confirm action?")) {
                    e.preventDefault();
                }
            }
        );
        //*******************************************
        //* RESPONSIVE LEFT NAV
        //*******************************************/
        $(document).on(
            "click",
            ".inbox-nav-toggle",
            function () {
                $(".inbox-left-menu").toggleClass("active");
            }
        );
        $(document).on(
            "click",
            ".left-menu li a",
            function () {
                $(".left-menu li .fa").removeClass("fa-folder-open")
                    .addClass("fa-folder-o");
                $(this).find(".fa").removeClass("fa-folder-o")
                    .addClass("fa-folder-open");
                $(".inbox-left-menu").toggleClass("active");
            }
        );

        //*******************************************
        //* SUB-FORMS
        //*******************************************/
        $(document).on(
            "click",
            ".sub-form a[data-cmd]",
            function (e) {
                var cmd = $(this).data("cmd");
                var row = $(this).closest(".row");
                var container = $(this).closest(".container");
                var url = container.data("formUrl");

                e.preventDefault();

                switch (cmd) {
                    case "add":
                        var data = {};
                        if (container.find(".row").length) {
                            data["row_id"] = container.find(".display-row").length;
                        }
                        $.ajax({
                            type: "GET",
                            url: url,
                            data: data,
                            success: function (result) {
                                container.append(result);
                                container.find(".empty-row").addClass("hidden");
                            }
                        });
                        break;
                    case "delete":
                        if (row.find("input[id$=id]").val() === "") {
                            row.remove();
                        } else {
                            row.find("input[id$=deleted]").val("yes");
                        }
                        row.addClass("hidden");
                        if (container.find(".display-row:not(.hidden)").length === 0)
                            container.find(".empty-row").removeClass("hidden");
                        break;
                }
            }
        );

        //*******************************************
        //* SETTINGS/SWITCHES
        //*******************************************/
        $(document).on(
            "change",
            ".inbox.new-message .settings .onoffswitch input[type=checkbox]",
            function () {
                var checked = $(this).is(":checked");
                var id = $(this).attr("id").replace("switch-", "");
                var container = $(this).closest(".settings");
                var values = container.find(".settings-values");
                var target = values.find(".settings-item[id$=" + id + "]");

                if ($(this).is(":checked")) {
                    if (target.length > 0) {
                        target.find("[id$=deleted]").val("no");
                    } else {
                        var row_id = values.find(".settings-item").length;
                        var url = container.data("formUrl");
                        $.ajax({
                            type: "GET",
                            url: url,
                            data: {
                                row_id: row_id,
                                id: id
                            },
                            success: function (result) {
                                values.append(result);
                            }
                        });
                    }
                } else {
                    if (target.length > 0) {
                        target.find("[id$=deleted]").val("yes");
                    }
                }
            }
        );

        //*******************************************
        //* TABLE-FORM EVENTS/FUNCTIONS
        //*******************************************/

        // Add new row
        $(document).on(
            "click",
            ".table-menu [data-cmd=add]," +
            " table .display-row td:not(.table-menu)",
            function (e) {
                var tab = $(this).closest(".tab-pane");
                var table = tab.find("table");
                var tbody = table.find("tbody");
                var cmd = $(this).data("cmd");
                var row = $(this).closest("tr.display-row");
                var row_id = row.data("rowId");
                var data = { };

                e.preventDefault();

                if (cmd === "add") {
                    row_id = tbody.find("tr:not(.empty-row)").length;
                } else {
                    data = row.find("input").serializeObject(function (name) {
                        return name.replace(/^([\w\-\d]+\.)/, "");
                    });
                }

                data["row_id"] = row_id;
                data["_csrf"] = $("#_csrf").val();

                $.ajax({
                    type: "POST",
                    url: table.data("formUrl"),
                    data: data,
                    success: function (result) {
                        if (result.indexOf('</tr>') !== -1 ) {        // inline-edit
                            tbody.find(".empty-row").addClass("hidden");

                            if (cmd === "add") {
                                tbody.append(result);
                            } else {
                                row.addClass("hidden");
                                $(result).insertAfter(row);
                            }
                        } else {                                      // form edit mode
                            table.hide();
                            tab.append(result);
                        }
                        tab.find(".table-form").validate();
                    }
                });
            }
        );

        // Update row
        $(document).on(
            "click",
            ".table-menu [data-cmd=update]",
            function (e) {
                var tab = $(this).closest(".tab-pane");
                var table = tab.find("table");
                var tbody = table.find("tbody");
                var form = $(this).closest(".table-form");
                var editRow = $(this).closest(".edit-row");
                var row_id = form.data("rowId");
                var row = tbody.find(".display-row[data-row-id=" + row_id + "]");

                e.preventDefault();

                if (!form.valid()) {
                    return;
                }

                form.ajaxSubmit({
                    type: "POST",
                    beforeSubmit: function () {
                        form.simulateLoading();
                    },
                    success: function (result) {
                        form.remove();
                        editRow.remove();
                        if (row.length === 0) {
                            tbody.append(result);
                        } else {
                            row.replaceWith(result);
                        }
                        tbody.find(".empty-row").addClass("hidden");
                        table.show();
                    }
                });
            }
        );
        // Cancel edit
        $(document).on(
            "click",
            ".table-menu [data-cmd=cancel]",
            function (e) {
                var tab = $(this).closest(".tab-pane");
                var table = tab.find("table");
                var tbody = table.find("tbody");
                var form = $(this).closest(".table-form");
                var editRow = $(this).closest(".edit-row");
                var row_id = form.data("rowId");
                var row = tbody.find(".display-row[data-row-id=" + row_id + "]");

                e.preventDefault();

                form.remove();
                editRow.remove();
                row.removeClass("hidden");
                table.show();

                if (tbody.find(".display-row:not(.hidden)").length === 0)
                    tbody.find(".empty-row").removeClass("hidden");
            }
        );
        // Delete row
        $(document).on(
            "click",
            ".table-menu [data-cmd=delete]",
            function (e) {
                var tab = $(this).closest(".tab-pane");
                var table = tab.find("table");
                var tbody = table.find("tbody");
                var row_id = $(this).data("rowId");
                var row = tbody.find("tr[data-row-id=" + row_id + "]");
                var deleted = row.find("input[id$=deleted]");

                e.preventDefault();

                deleted.val("yes");
                row.removeClass("edit-row").addClass("hidden");
                tab.find(".table-form").remove();
                table.show();

                if (tbody.find(".display-row:not(.hidden)").length === 0)
                    tbody.find(".empty-row").removeClass("hidden");
            }
        );

        return this;
    };
}(jQuery));

$(function () {

    //************************
    //*    MAIN NAVIGATION
    //************************/
    $(".main-menu .js-sub-menu-toggle").click(function (e) {

        e.preventDefault();

        var $li = $(this).parent("li");
        if (!$li.hasClass("active")) {
            $li.find(" > a .toggle-icon").removeClass("fa-angle-left").addClass("fa-angle-down");
            $li.addClass("active");
        }
        else {
            $li.find(" > a .toggle-icon").removeClass("fa-angle-down").addClass("fa-angle-left");
            $li.removeClass("active");
        }

        $li.find(" > .sub-menu").slideToggle(300);
    });

    $(".js-toggle-minified").clickToggle(
        function () {
            $(".left-sidebar").addClass("minified");
            $(".content-wrapper").addClass("expanded");

            $(".left-sidebar .sub-menu")
                .css("display", "none")
                .css("overflow", "hidden");

            $(".main-menu > li > a > .text").animate({
                opacity: 0
            }, 200);

            $(".sidebar-minified").find("i.fa-angle-left").toggleClass("fa-angle-right");
        },
        function () {
            $(".left-sidebar").removeClass("minified");
            $(".content-wrapper").removeClass("expanded");
            $(".main-menu > li > a > .text").animate({
                opacity: 1
            }, 600);

            $(".sidebar-minified").find("i.fa-angle-left").toggleClass("fa-angle-right");
        }
    );

    // main responsive nav toggle
    $(".main-nav-toggle").clickToggle(
        function () {
            $(".left-sidebar").slideDown(300);
        },
        function () {
            $(".left-sidebar").slideUp(300);
        }
    );


    //************************
    //*	WINDOW RESIZE
    //************************/
    $(window).on(
        "resize",
        function () {
            var sidebar = $(".left-sidebar");
            if ($(window).width() < (992 - 15)) {
                if (sidebar.hasClass("minified")) {
                    sidebar.removeClass("minified")
                        .addClass("init-minified");
                }

            } else {
                if (sidebar.hasClass("init-minified")) {
                    sidebar.removeClass("init-minified")
                        .addClass("minified");
                }
            }
        }
    );

    //************************
    //*    BOOTSTRAP TOOLTIP
    //************************/
    $("body").tooltip({selector: "[data-toggle=tooltip]"});

    //************************
    //*    BOOTSTRAP ALERT
    //************************/
    if ($(".alert").length > 0) {
        $(".alert .close").click(function (e) {
            e.preventDefault();
            $(this).parents(".alert").fadeOut(300);
        });
    }

    //************************
    //*	INBOX PAGE
    //************************/
    var form_grid = $("#form-grid");
    if (form_grid.length > 0) {
        form_grid.ajaxForm({
            beforeSubmit: function () {
                $(".messages").simulateLoading();
            },
            success: function (result) {
                $(".inbox-content").html(result);
            }
        });
        $(".inbox.grid").attachGridPlugins();
    }

    var form_entry = $("#form-entry");
    if (form_entry.length > 0) {
        var container = $(".inbox.new-message");
        var $submit = form_entry.find("#submit");
        var $title = $submit.data("gritterTitle");

        form_entry.validate();
        form_entry.ajaxForm({
            beforeSubmit: function () {
                container.simulateLoading();
            },
            success: function (result) {
                container.html(result).attachFormPlugins();
                if (container.find("ul.error>li").length) {
                    $.gritter.add({
                        title: $title,
                        text: "An error occured while saving to database."
                    });
                } else {
                    $.gritter.add({
                        title: $title,
                        text: "Record has been successfully saved."
                    });
                }
            }
        });
        container.attachFormPlugins();
        container.attachFormEvents();
    }
});
